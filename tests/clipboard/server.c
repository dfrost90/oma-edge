#include <wayland-server.h>
#include <wayland-server-protocol.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>
#include <sys/wait.h>

/* Private, minimal Wayland server: never connects to the desktop compositor.
 * The provider sends at most 128 KiB over four seconds, never an infinite stream.
 */
static struct wl_display *display;
static struct wl_resource *device;
static int ticks;
static struct wl_event_source *timer;
static void destroy(struct wl_client *c, struct wl_resource *r) { wl_resource_destroy(r); }
static void accept_offer(struct wl_client *c, struct wl_resource *r, uint32_t s, const char *m) {}
static void receive(struct wl_client *c, struct wl_resource *r, const char *mime, int32_t fd) {
    fprintf(stderr, "RECEIVE %s\n", mime); fflush(stderr);
    if (fork() == 0) {
        char buf[4096]; memset(buf, '7', sizeof buf);
        for (int i=0; i<32; ++i) {
            if (write(fd, buf, sizeof buf) < 0) break;
            usleep(125000);
        }
        close(fd); _exit(0);
    }
    close(fd);
}
static const struct wl_data_offer_interface offer_impl = {
    .accept=accept_offer, .receive=receive, .destroy=destroy
};
static void start_drag(struct wl_client *c, struct wl_resource *r, struct wl_resource *s, struct wl_resource *o, struct wl_resource *i, uint32_t n) {}
static void set_selection(struct wl_client *c, struct wl_resource *r, struct wl_resource *s, uint32_t n) {}
static const struct wl_data_device_interface device_impl = {
    .start_drag=start_drag, .set_selection=set_selection, .release=destroy
};
static void source(struct wl_client *c, struct wl_resource *r, uint32_t id) {}
static void get_device(struct wl_client *c, struct wl_resource *r, uint32_t id, struct wl_resource *seat) {
    device=wl_resource_create(c, &wl_data_device_interface, 1, id);
    wl_resource_set_implementation(device, &device_impl, NULL, NULL);
}
static const struct wl_data_device_manager_interface manager_impl = { .create_data_source=source, .get_data_device=get_device };
static void bind_manager(struct wl_client *c, void *d, uint32_t v, uint32_t id) {
    struct wl_resource *r=wl_resource_create(c,&wl_data_device_manager_interface,1,id);
    wl_resource_set_implementation(r,&manager_impl,NULL,NULL);
}
static const struct wl_seat_interface seat_impl = {0};
static void bind_seat(struct wl_client *c, void *d, uint32_t v, uint32_t id) {
    struct wl_resource *r=wl_resource_create(c,&wl_seat_interface,1,id);
    wl_resource_set_implementation(r,&seat_impl,NULL,NULL);
    wl_seat_send_capabilities(r,0);
}
static void bind_output(struct wl_client *c, void *d, uint32_t v, uint32_t id) {
    struct wl_resource *r=wl_resource_create(c,&wl_output_interface,2,id);
    wl_resource_set_implementation(r,NULL,NULL,NULL);
    wl_output_send_geometry(r,0,0,300,200,WL_OUTPUT_SUBPIXEL_UNKNOWN,"Test","Isolated",WL_OUTPUT_TRANSFORM_NORMAL);
    wl_output_send_mode(r,WL_OUTPUT_MODE_CURRENT|WL_OUTPUT_MODE_PREFERRED,800,600,60000);
    wl_output_send_scale(r,1); wl_output_send_done(r);
}
static const struct wl_compositor_interface compositor_impl = {0};
static void bind_compositor(struct wl_client *c, void *d, uint32_t v, uint32_t id) {
    struct wl_resource *r=wl_resource_create(c,&wl_compositor_interface,1,id);
    wl_resource_set_implementation(r,&compositor_impl,NULL,NULL);
}
static const struct wl_shell_interface shell_impl = {0};
static void bind_shell(struct wl_client *c, void *d, uint32_t v, uint32_t id) {
    struct wl_resource *r=wl_resource_create(c,&wl_shell_interface,1,id);
    wl_resource_set_implementation(r,&shell_impl,NULL,NULL);
}
static int tick(void *data) {
    ++ticks;
    if (device && ticks == 1) {
        struct wl_resource *offer=wl_resource_create(wl_resource_get_client(device),&wl_data_offer_interface,1,0);
        wl_resource_set_implementation(offer,&offer_impl,NULL,NULL);
        wl_data_device_send_data_offer(device,offer);
        wl_data_offer_send_offer(offer,"text/plain");
        wl_data_offer_send_offer(offer,"text/plain;charset=utf-8");
        wl_data_device_send_selection(device,offer);
        fprintf(stderr,"SELECTION %d\n",ticks); fflush(stderr);
    }
    if (ticks >= 12) wl_display_terminate(display);
    else wl_event_source_timer_update(timer,1000);
    return 0;
}
int main(void) {
    signal(SIGPIPE,SIG_IGN); signal(SIGCHLD,SIG_IGN);
    display=wl_display_create();
    wl_global_create(display,&wl_compositor_interface,1,NULL,bind_compositor);
    wl_global_create(display,&wl_seat_interface,1,NULL,bind_seat);
    wl_global_create(display,&wl_output_interface,2,NULL,bind_output);
    wl_global_create(display,&wl_data_device_manager_interface,1,NULL,bind_manager);
    wl_display_init_shm(display);
    wl_global_create(display,&wl_shell_interface,1,NULL,bind_shell);
    if(wl_display_add_socket(display,"clipboard-test")) return 1;
    timer=wl_event_loop_add_timer(wl_display_get_event_loop(display),tick,NULL);
    wl_event_source_timer_update(timer,1000);
    wl_display_run(display);
    wl_display_destroy_clients(display);
    wl_display_destroy(display);
    return 0;
}
