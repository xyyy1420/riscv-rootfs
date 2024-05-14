import multiprocessing
import os
import random

manager = multiprocessing.Manager()
checkpoint_res = manager.list()
checkpoint_lock = manager.Lock()


def append_checkpoint_result(res):
    checkpoint_lock.acquire()
    if res not in checkpoint_res:
        checkpoint_res.append(res)
    checkpoint_lock.release()


def get_checkpoint_results():
    checkpoint_lock.acquire()
    res = checkpoint_res
    checkpoint_lock.release()
    return res


default_config = {
    "logs": "logs",
    "buffer": "test_buffer",
    "archive_folder": "archive",
    "archive_id": "",
    "elf_suffix": "_base.riscv64-linux-gnu-gcc12.2.0",
    "bin_suffix": "-bbl-linux-spec.bin",
    "gcpt_bin_suffix": "-gcpt-pk-linux-spec.bin",
    "cpu2006_run_dir": "",
    "riscv-rootfs": "",
    "pk": "",
    "nemu_home": "",
    "qemu_home": "",
    "qemu_plugin": "",
    "profiling_times": 1,
    "cluster_times": 1,
    "checkpoint_times": 1,
    "profiling_id": 0,
    "cluster_id": 0,
    "checkpoint_id": 0,
    "emulator": "NEMU"
}


def def_config():
    return default_config


def prepare_config():
    return {
        "prepare_log":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"], "prepare"),
        "elf_folder":
        os.path.join(def_config()["buffer"], "elf"),
    }


def build_config():
    return {
        "build_log":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"], "build"),
        "bin_folder":
        os.path.join(def_config()["buffer"], "bin"),
        "scripts_folder":
        os.path.join(def_config()["buffer"], "scripts"),
        "gcpt_bin_folder":
        os.path.join(def_config()["buffer"], "gcpt_bins"),
        "assembly_folder":
        os.path.join(def_config()["buffer"], "assembly"),
    }


default_simpoint_config = {
    "profiling_format": "profiling-{}",
    "cluster_format": "cluster-{}-{}",
    "checkpoint_format": "checkpoint-{}-{}-{}",
    "json_format": "cluster-{}-{}.json",
    "list_format": "checkpoint-{}-{}-{}.lst",
}


#default_simpoint_config=
def simpoint_config():
    return {
        "qemu":
        os.path.join(def_config()["qemu_home"], "build",
                     "qemu-system-riscv64"),
        "profiling_plugin":
        os.path.join(def_config()["qemu_plugin"]),
        "nemu":
        os.path.join(def_config()["nemu_home"], "build",
                     "riscv64-nemu-interpreter"),
        "gcpt_restore":
        os.path.join(def_config()["nemu_home"], "resource", "gcpt_restore",
                     "build", "gcpt.bin"),
        "simpoint":
        os.path.join(def_config()["nemu_home"], "resource", "simpoint",
                     "simpoint_repo", "bin", "simpoint"),
        "bbl_folder":
        os.path.join(build_config()["bin_folder"]),
        "gcpt_bin_folder":
        os.path.join(build_config()["gcpt_bin_folder"]),
        "profiling_folder":
        default_simpoint_config["profiling_format"],
        "cluster_folder":
        default_simpoint_config["cluster_format"],
        "checkpoint_folder":
        default_simpoint_config["checkpoint_format"],
        "json_file":
        default_simpoint_config["json_format"],
        "list_file":
        default_simpoint_config["list_format"],
        "profiling_logs":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"],
                     default_simpoint_config["profiling_format"]),
        "cluster_logs":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"],
                     default_simpoint_config["cluster_format"]),
        "checkpoint_logs":
        os.path.join(def_config()["buffer"],
                     def_config()["logs"],
                     default_simpoint_config["checkpoint_format"]),
        "interval":
        "20000000",
    }


def profiling_command(workload, profiling_folder):
    command = [
        simpoint_config()["nemu"],
        "{}/{}{}".format(simpoint_config()["bbl_folder"], workload,
                         def_config()["bin_suffix"]), "-D",
        def_config()["buffer"], "-w", workload, "-C", profiling_folder, "-b",
        "--simpoint-profile", "--cpt-interval",
        simpoint_config()["interval"], "-r",
        simpoint_config()["gcpt_restore"]
    ]
    return command


def qemu_profiling_command(workload, profiling_folder):
    command = [
        simpoint_config()["qemu"], "-bios",
        "{}/{}{}".format(simpoint_config()["gcpt_bin_folder"], workload,
                         def_config()["gcpt_bin_suffix"]), "-M", "nemu",
        "-nographic", "-m", "8G", "-smp", "1", "-cpu", "rv64,v=true,vlen=128",
        "-plugin", "{},workload={},intervals={},target={}".format(
            simpoint_config()["profiling_plugin"], workload,
            simpoint_config()["interval"], os.path.join(def_config()["buffer"],profiling_folder,workload))
    ]
    return command


def cluster_command(workload, profiling_folder, cluster_folder):
    seedkm = random.randint(100000, 999999)
    seedproj = random.randint(100000, 999999)
    command = [
        simpoint_config()["simpoint"], "-loadFVFile",
        os.path.join(profiling_folder, workload,
                     "simpoint_bbv.gz"), "-saveSimpoints",
        os.path.join(cluster_folder, "simpoints0"), "-saveSimpointWeights",
        os.path.join(cluster_folder, "weights0"), "-inputVectorsGzipped",
        "-maxK", "100", "-numInitSeeds", "2", "-iters", "1000", "-seedkm",
        f"{seedkm}", "-seedproj", f"{seedproj}"
    ]
    return command


def checkpoint_command(workload, cluster_folder, checkpoint_folder):
    command = [
        simpoint_config()["nemu"],
        "{}/{}{}".format(simpoint_config()["bbl_folder"], workload,
                         def_config()["bin_suffix"]), "-D",
        def_config()["buffer"], "-w", workload, "-C", checkpoint_folder, "-b",
        "-S", cluster_folder, "--cpt-interval",
        simpoint_config()["interval"], "-r",
        simpoint_config()["gcpt_restore"]
    ]
    return command


def qemu_checkpoint_command(workload, cluster_folder, checkpoint_folder):
    command = [
        simpoint_config()["qemu"], "-bios",
        "{}/{}{}".format(simpoint_config()["gcpt_bin_folder"], workload,
                         def_config()["gcpt_bin_suffix"]), "-M", "nemu",
        "-nographic", "-m", "8G", "-smp", "1", "-cpu", "rv64,v=true,vlen=128",
        "-simpoint-path", cluster_folder, "-workload", workload,
        "-cpt-interval",
        simpoint_config()["interval"], "-output-base-dir",
        def_config()["buffer"], "-config-name", checkpoint_folder,
        "-checkpoint-mode", "SimpointCheckpoint"
    ]
    return command


def get_default_initramfs_file():
    return [
        "dir /bin 755 0 0", "dir /etc 755 0 0", "dir /dev 755 0 0",
        "dir /lib 755 0 0", "dir /proc 755 0 0", "dir /sbin 755 0 0",
        "dir /sys 755 0 0", "dir /tmp 755 0 0", "dir /usr 755 0 0",
        "dir /mnt 755 0 0", "dir /usr/bin 755 0 0", "dir /usr/lib 755 0 0",
        "dir /usr/sbin 755 0 0", "dir /var 755 0 0", "dir /var/tmp 755 0 0",
        "dir /root 755 0 0", "dir /var/log 755 0 0", "",
        "nod /dev/console 644 0 0 c 5 1", "nod /dev/null 644 0 0 c 1 3", "",
        "# libraries",
        "file /lib/ld-linux-riscv64-lp64d.so.1 ${RISCV}/sysroot/lib/ld-linux-riscv64-lp64d.so.1 755 0 0",
        "file /lib/libc.so.6 ${RISCV}/sysroot/lib/libc.so.6 755 0 0",
        "file /lib/libresolv.so.2 ${RISCV}/sysroot/lib/libresolv.so.2 755 0 0",
        "file /lib/libm.so.6 ${RISCV}/sysroot/lib/libm.so.6 755 0 0",
        "file /lib/libdl.so.2 ${RISCV}/sysroot/lib/libdl.so.2 755 0 0",
        "file /lib/libpthread.so.0 ${RISCV}/sysroot/lib/libpthread.so.0 755 0 0",
        "", "# busybox",
        "file /bin/busybox {}/rootfsimg/build/busybox 755 0 0".format(
            def_config()["riscv-rootfs"]),
        "file /etc/inittab {}/rootfsimg/inittab-spec 755 0 0".format(
            def_config()["riscv-rootfs"]), "slink /init /bin/busybox 755 0 0",
        "", "# SPEC common", "dir /spec_common 755 0 0",
        "file /spec_common/before_workload {}/rootfsimg/build/before_workload 755 0 0"
        .format(def_config()["riscv-rootfs"]),
        "file /spec_common/trap {}/rootfsimg/build/qemu_trap 755 0 0".format(
            def_config()["riscv-rootfs"]), "", "# SPEC", "dir /spec 755 0 0",
        "file /spec/run.sh {}/rootfsimg/run.sh 755 0 0".format(
            def_config()["riscv-rootfs"])
    ]


def get_spec_elf_list():
    return [
        "astar", "bwaves", "bzip2", "cactusADM", "calculix", "dealII",
        "gamess", "GemsFDTD", "gobmk", "gromacs", "h264ref", "hmmer", "lbm",
        "leslie3d", "libquantum", "mcf", "milc", "namd", "omnetpp",
        "perlbench", "povray", "sjeng", "soplex", "specrand", "sphinx3",
        "tonto", "wrf", "xalancbmk", "zeusmp", "gcc"
    ]


def get_default_spec_list():
    return [
        "astar_biglakes",
        "astar_rivers",
        "bwaves",
        "bzip2_chicken",
        "bzip2_combined",
        "bzip2_html",
        "bzip2_liberty",
        "bzip2_program",
        "bzip2_source",
        "cactusADM",
        "calculix",
        "dealII",
        "gamess_cytosine",
        "gamess_gradient",
        "gamess_triazolium",
        "gcc_166",
        "gcc_200",
        "gcc_cpdecl",
        "gcc_expr2",
        "gcc_expr",
        "gcc_g23",
        "gcc_s04",
        "gcc_scilab",
        "gcc_typeck",
        "GemsFDTD",
        "gobmk_13x13",
        "gobmk_nngs",
        "gobmk_score2",
        "gobmk_trevorc",
        "gobmk_trevord",
        "gromacs",
        "h264ref_foreman.baseline",
        "h264ref_foreman.main",
        "h264ref_sss",
        "hmmer_nph3",
        "hmmer_retro",
        "lbm",
        "leslie3d",
        "libquantum",
        "mcf",
        "milc",
        "namd",
        "omnetpp",
        "perlbench_checkspam",
        "perlbench_diffmail",
        "perlbench_splitmail",
        "povray",
        "sjeng",
        "soplex_pds-50",
        "soplex_ref",
        "sphinx3",
        "tonto",
        "wrf",
        "xalancbmk",
        "zeusmp",
    ]
