// Mario Tennis Fever's own SDK replacements (mtf-recomp): the calls nxboot (exefs/main) makes that Mario Kart World
// never did.
//
// nxboot's boot function (main+0x660) mounts the RomFS, registers the .nrr with nn::ro, unpacks the engine into a
// buffer with six threads and hands it to nn::ro::LoadModule; nnMain then calls the engine's one export, Abort()
// (docs/research.md, "The engine payload"). Here the engine is already mapped and linked at boot as the module
// "basic" (lifted from tools/unpack_engine.py's copy), so LoadModule checks that the buffer nxboot built is that same
// engine and runs its constructors, as ro does on the console.
#include <stdint.h>
#include <string.h>

#include "host.h"
#include "ov.h"
#include "version.h"

void rt_boot_ro_init(Cpu *c, const char *name);   // boot.c

static void ov_nothing(Cpu *c) { (void)c; }
static void ov_ok(Cpu *c) { ret_x(c, 0); }

// Result nn::ro::Initialize(): an IPC to ldr:ro on the console, so its caller blocks and the threads it has started
// run first. nxboot's six unpacking threads read their arguments from its stack, which it reuses right after
// (kern_settle in kernel.c says how); 50 ms is far more than their first steps take.
static void ov_ro_initialize(Cpu *c) {
    int pending = kern_settle(50000000);
    if (pending) rt_log("ov_mtf: nn::ro::Initialize: %d started threads had not run after 50 ms", pending);
    ret_x(c, 0);
}

static const RtLoaded *loaded(const char *name) {
    for (int i = 0; i < ldr_count(); i++)
        if (!strcmp(ldr_module(i)->name, name)) return ldr_module(i);
    rt_fatal("ov_mtf: module %s is not loaded", name);
}

// Result nn::ro::GetBufferSize(size_t *size, const void *image): the engine's .bss is part of the image the loader
// mapped, so ro needs no buffer.
static void ov_ro_buffer_size(Cpu *c) {
    ST64(arg_x(c, 0), 0);
    ret_x(c, 0);
}

// Result nn::ro::LoadModule(Module *module, const void *image, void *buffer, size_t size, int bind)
static void ov_ro_load_module(Cpu *c) {
    const char *name = rt_version()->ro_module;
    if (!name) rt_fatal("ov_mtf: nn::ro::LoadModule, but this game version names no ro module");
    const RtLoaded *m = loaded(name);
    const uint8_t *image = (const uint8_t *)(uintptr_t)arg_x(c, 1);
    // text and rodata are as the file has them (relocations only write the data segment, loader.c)
    if (memcmp(image, (const void *)(uintptr_t)m->base, m->data_off))
        rt_fatal("ov_mtf: the module nxboot built is not %s as tools/unpack_engine.py rebuilt it", name);
    rt_log("ov_mtf: nn::ro::LoadModule: nxboot's buffer is %s (%#llx bytes of code and rodata agree)", name,
           (unsigned long long)m->data_off);
    rt_boot_ro_init(c, name);
    ret_x(c, 0);
}

HOST_OVERRIDE("_ZN2nn2fs12SetAllocatorEPFPvmEPFvS1_mE", ov_nothing);
HOST_OVERRIDE("_ZN2nn2ro10InitializeEv", ov_ro_initialize);
HOST_OVERRIDE("_ZN2nn2ro18RegisterModuleInfoEPNS0_16RegistrationInfoEPKv", ov_ok);
HOST_OVERRIDE("_ZN2nn2ro13GetBufferSizeEPmPKv", ov_ro_buffer_size);
HOST_OVERRIDE("_ZN2nn2ro10LoadModuleEPNS0_6ModuleEPKvPvmi", ov_ro_load_module);

// ==== nn::friends, offline: what Mario Tennis Fever's engine asks that Mario Kart World does not (ov_net.c has the
// rest). The console with no network: an empty notification queue whose event never fires, no invitations, and the
// online play session declarations accepted. Results for the online calls: friends' module (121), any failure keeps
// the game on its offline path, as ov_net.c's nifm results do.
#define FRIENDS_R_UNAVAILABLE (121u | (1u << 9))

static uint64_t queue_event, invitation_event;   // nn::os::SystemEventType of each, in runtime memory

static uint64_t bound_event(Cpu *c, uint64_t *ev, const char *what) {
    if (!*ev) {
        *ev = mem_runtime_alloc(0x1000, what);
        if (!*ev) rt_fatal("ov_mtf: no memory for %s", what);
        kern_bind_system_event(c, *ev, 0);   // manual clear, never signalled
    }
    return *ev;
}

// Result NotificationQueue::Initialize(const account::Uid &), void Finalize()
static void ov_queue_ok(Cpu *c) { ret_x(c, 0); }
// nn::os::SystemEvent *NotificationQueue::GetSystemEvent(), nn::os::SystemEvent *GetFriendInvitationNotificationEvent()
static void ov_queue_event(Cpu *c) { ret_x(c, bound_event(c, &queue_event, "friends notification event")); }
static void ov_invitation_event(Cpu *c) { ret_x(c, bound_event(c, &invitation_event, "friends invitation event")); }
// Result NotificationQueue::Pop(NotificationInfo *): nothing queued
static void ov_queue_pop(Cpu *c) { ret_x(c, FRIENDS_R_UNAVAILABLE); }
// account::Uid NotificationQueue::GetUid() const: the local user (returned in x0, x1)
static void ov_queue_uid(Cpu *c) {
    uint64_t uid[2];
    account_uid(uid);
    c->x[0] = uid[0];
    c->x[1] = uid[1];
}
// bool TryPopFriendInvitationNotificationInfo(account::Uid *, size_t *, void *, size_t): none
static void ov_no_invitation(Cpu *c) { ret_x(c, 0); }
static void ov_friends_unavailable(Cpu *c) { ret_x(c, FRIENDS_R_UNAVAILABLE); }

HOST_OVERRIDE("_ZN2nn7friends17NotificationQueue10InitializeERKNS_7account3UidE", ov_queue_ok);
HOST_OVERRIDE("_ZN2nn7friends17NotificationQueue8FinalizeEv", ov_nothing);
HOST_OVERRIDE("_ZN2nn7friends17NotificationQueue14GetSystemEventEv", ov_queue_event);
HOST_OVERRIDE("_ZN2nn7friends17NotificationQueue3PopEPNS0_16NotificationInfoE", ov_queue_pop);
HOST_OVERRIDE("_ZNK2nn7friends17NotificationQueue6GetUidEv", ov_queue_uid);
HOST_OVERRIDE("_ZN2nn7friends36GetFriendInvitationNotificationEventEv", ov_invitation_event);
HOST_OVERRIDE("_ZN2nn7friends38TryPopFriendInvitationNotificationInfoEPNS_7account3UidEPmPvm", ov_no_invitation);
HOST_OVERRIDE("_ZN2nn7friends28DeclareOpenOnlinePlaySessionERKNS_7account3UidE", ov_ok);
HOST_OVERRIDE("_ZN2nn7friends29DeclareCloseOnlinePlaySessionERKNS_7account3UidE", ov_ok);
HOST_OVERRIDE("_ZN2nn7friends21StartFriendInvitationERKNS_7account3UidEiRKNS0_35FriendInvitationGameModeDescriptionEPKvm",
              ov_friends_unavailable);
HOST_OVERRIDE("_ZN2nn7friends16UpdateFriendInfoEPNS0_6FriendERKNS_7account3UidEPKNS3_23NetworkServiceAccountIdEi",
              ov_friends_unavailable);
