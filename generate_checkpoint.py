import argparse
import os
import shutil
import subprocess
import time
from threading import Thread
from multiprocessing import Pool
import random
from datetime import datetime
from utils import mkdir, file_entrys, app_list
from configs import build_config, get_default_spec_list, get_spec_elf_list, def_config, prepare_config, get_default_spec_list, default_config, get_checkpoint_results
from simpoint import per_checkpoint_generate_worklist, per_checkpoint_generate_json, simpoint
from spec_gen import generate_initramfs, generate_run_sh

def generate_archive_info(message):
    with open(os.path.join(def_config()["archive_folder"], "archive_info"),
              "a") as f:
        f.write("{}: {}\n".format(def_config()["archive_id"],message))


def create_folders():
    for value in build_config().values():
        mkdir(value)
    for value in prepare_config().values():
        mkdir(value)


def gen_copy_list_item(src_name,
                       src_path,
                       append_elf_suffix=def_config()["elf_suffix"]):
    target_path = ""
    for program in get_spec_elf_list():
        if src_name.find(program) != -1:
            target_path = os.path.join(prepare_config()["elf_folder"],
                                       program + append_elf_suffix)
            return ([src_path, target_path])
    else:
        return []


def prepare_elf_buffer(source_elf_path):
    prepare_copy_list = []
    copy_threads = []

    for entry in file_entrys(source_elf_path):
        item = gen_copy_list_item(entry.name, entry.path,def_config()["elf_suffix"])
        if item != []:
            prepare_copy_list.append(item)
            thread = Thread(target=shutil.copy, args=item)
            thread.start()
            copy_threads.append(thread)

    for thread in copy_threads:
        thread.join()

    for item in prepare_copy_list:
        with open(os.path.join(os.path.join(build_config()["assembly_folder"],os.path.basename(item[1])+".s")),"w") as out:
            res = subprocess.run(["riscv64-unknown-linux-gnu-objdump", "-d",item[1]],stdout=out)
            res.check_returncode()



def build_bbl_as_gcpt_payload(spec):
    with open(
            os.path.join(build_config()["build_log"], f"build-{spec}-aspayload-out.log"),
            "w") as out, open(
                os.path.join(build_config()["build_log"],
                             f"build-{spec}-aspayload-err.log"), "w") as err:

        res = subprocess.run(["make", "clean"],
                             cwd=os.path.join(def_config()["nemu_home"],"resource","gcpt_restore"),
                             stdout=out,
                             stderr=err)
        res.check_returncode()

        res = subprocess.run(["make", "GCPT_PAYLOAD_PATH={}".format(os.path.abspath(os.path.join(build_config()["bin_folder"], "{}{}".format(spec,def_config()["bin_suffix"]))))],
                             cwd=os.path.join(def_config()["nemu_home"],"resource","gcpt_restore"),
                             stdout=out,
                             stderr=err)
        res.check_returncode()

    gcpt_bin_src_path = os.path.join(def_config()["nemu_home"], "resource", "gcpt_restore","build","gcpt.bin")
    gcpt_bin_dest_path = os.path.join(build_config()["gcpt_bin_folder"], "{}{}".format(spec,def_config()["gcpt_bin_suffix"]))
    shutil.copy(gcpt_bin_src_path, gcpt_bin_dest_path)

    gcpt_txt_src_path= os.path.join(def_config()["nemu_home"], "resource", "gcpt_restore","build","gcpt.txt")
    gcpt_txt_dest_path = os.path.join(build_config()["assembly_folder"], "{}{}{}".format(spec,def_config()["gcpt_bin_suffix"],".gcpt.s"))
    shutil.copy(gcpt_txt_src_path, gcpt_txt_dest_path)


def build_spec_bbl(spec):

    print(f"build {spec}-bbl-linux-spec...")

    with open(
            os.path.join(build_config()["build_log"], f"build-{spec}-out.log"),
            "w") as out, open(
                os.path.join(build_config()["build_log"],
                             f"build-{spec}-err.log"), "w") as err:
        res = subprocess.run(["make", "clean"],
                             cwd=def_config()["pk"],
                             stdout=out,
                             stderr=err)
        res.check_returncode()
        res = subprocess.run(["make", "-j70"],
                             cwd=def_config()["pk"],
                             stdout=out,
                             stderr=err)
        res.check_returncode()

    bbl_bin_src_path = os.path.join(def_config()["pk"], "build", "bbl.bin")
    bbl_bin_dest_path = os.path.join(build_config()["bin_folder"], "{}{}".format(spec,def_config()["bin_suffix"]))
    shutil.copy(bbl_bin_src_path, bbl_bin_dest_path)

    bbl_txt_src_path = os.path.join(def_config()["pk"], "build", "bbl.txt")
    bbl_txt_dest_path = os.path.join(build_config()["assembly_folder"], "{}{}{}".format(spec,def_config()["bin_suffix"],".pk.s"))
    shutil.copy(bbl_txt_src_path, bbl_txt_dest_path)

    kernel_txt_src_path = os.path.join(def_config()["pk"], "build", "vmlinux.txt")
    kernel_txt_dest_path = os.path.join(build_config()["assembly_folder"], "{}{}{}".format(spec,def_config()["bin_suffix"],".vmlinux.s"))
    shutil.copy(kernel_txt_src_path, kernel_txt_dest_path)




def prepare_rootfs(spec, withTrap=True):
    generate_initramfs(spec,
                       def_config()["elf_suffix"],
                       os.path.join(def_config()["riscv-rootfs"],"rootfsimg"))
    generate_run_sh(spec,
                    def_config()["elf_suffix"],
                    os.path.join(def_config()["riscv-rootfs"],"rootfsimg"), withTrap)


def run_simpoint(spec_app):
    simpoint(def_config()["profiling_times"],
             def_config()["cluster_times"],
             def_config()["checkpoint_times"], spec_app)


def err_check(err):
    print("Error happend", err)


def gen_env_script():
    env_dist=os.environ
    keys=["RISCV","NOOP_HOME","NEMU_HOME","RISCV_ROOTFS_HOME"]
    with open("auto_checkpoint_env.sh","w") as f:
        for key in keys:
            print("export {}={}".format(key,env_dist.get(key)),file=f)

def delete_archive():
    (_,archive_id)=os.path.split(def_config()["buffer"])
    shutil.rmtree(def_config()["buffer"])
    result=[]
    with open(os.path.join(def_config()["archive_folder"],"archive_info"),"r") as f:
        infos=f.readlines()
        for info in infos:
            if archive_id in info:
                pass
            else:
                result.append(info)

    with open(os.path.join(def_config()["archive_folder"],"archive_info"),"w") as f:
        f.writelines(result)


if __name__ == "__main__":
    gen_env_script()

    parser = argparse.ArgumentParser(
        description="Auto profiling and checkpointing")
    parser.add_argument('--elfs',
                        help="Local spec programs folder (elf format)")
    parser.add_argument('--archive-folder',
                        help="Archive folder name (default: archive)")
    parser.add_argument(
        '--elf-suffix',
        help=
        "Elf suffix in spec-bbl (default: _base.riscv64-linux-gnu-gcc12.2.0)")
    parser.add_argument(
        '--spec-app-list',
        help="List of selected spec programs path (default: all spec program)")
    parser.add_argument(
        '--spec-apps',
        help='List of selected spec programs (default: null; format: "astar_biglakes,astar_rivers" )')
    parser.add_argument('--print-spec-app-list',
                        action="store_true",
                        help="Print default spec program list)")
    parser.add_argument('--message', help="Record info to the archive")
    parser.add_argument(
        '--spec-bbl-checkpoint-mode',
        action='store_true',
        help="Generate spec bbl mode (set with before_workload,trap or not)")

    parser.add_argument(
        '--times',
        help=
        "Profiing cluster checkpoint times (default: 1,1,1;(format 1,1,1) if set it manual, you must set archive id and ensure profiling id, cluster id, checkpoint id is ok)"
    )
    parser.add_argument(
        '--start-id',
        help=
        "Profiing cluster checkpoint start id (default: 0,0,0;(format 0,0,0) if set it manual, it will overwrite some result which is exists)"
    )

    parser.add_argument(
        '--archive-id',
        help="Archive id (default: use the md5 of the current time)")
    parser.add_argument(
        '--max-threads',
        help="Max threads, must less then cpu nums (default: 10)")
    parser.add_argument('--build-bbl-only',
                        action='store_true',
                        help="Generate spec bbl only")
    parser.add_argument('--delete',
                        action='store_true',
                        help="Delete archive")

    parser.add_argument('--emulator',
                        help="Specify the emulator (default: NEMU), options: NEMU, QEMU")


    args = parser.parse_args()

    if args.print_spec_app_list:
        print(get_default_spec_list())
        exit(0)

    # set user profiling, cluster, checkpoint times
    if args.times != None:
        profiling_times, cluster_times, checkpoint_times = args.times.split(
            ',')
        default_config["profiling_times"] = int(profiling_times)
        default_config["cluster_times"] = int(cluster_times)
        default_config["checkpoint_times"] = int(checkpoint_times)

    if args.start_id != None:
        profiling_id, cluster_id, checkpoint_id = args.start_id.split(',')
        default_config["profiling_id"] = int(profiling_id)
        default_config["cluster_id"] = int(cluster_id)
        default_config["checkpoint_id"] = int(checkpoint_id)

    if (def_config()["profiling_times"] == 0 or def_config()["cluster_times"]
            == 0 or def_config()["cluster_times"] == 0) and (args.archive_id
                                                             == None):
        print("Error: When times has 0, you must set archive id")
        exit(1)

    # user set elf suffix
    if args.elf_suffix != None:
        default_config["elf_suffix"] = args.elf_suffix

    # user set archive folder
    if args.archive_folder != None:
        default_config["archive_folder"] = args.archive_folder

    # calculate result archive id
    with open("random_words","r") as f:
        lines = f.read().splitlines()
        default_config["archive_id"]="{}-{}-{}-{}".format(random.choice(lines),random.choice(lines),random.choice(lines),datetime.now().strftime("%Y-%m-%d-%H-%M"))

    # set archive id from arg
    if args.archive_id != None:
        default_config["archive_id"] = args.archive_id

    default_config["buffer"] = os.path.join(def_config()["archive_folder"],
                                            def_config()["archive_id"])
    if args.delete:
        delete_archive()
        exit(0)

    # record user message
    if args.message == None:
        print("Warning: Without message might could not find profiling result")
        args.message = "No message"

    if args.emulator != None:
        if args.emulator=="NEMU":
            default_config["emulator"]="NEMU"
        else:
            default_config["emulator"]="QEMU"


    create_folders()
    assert (os.path.exists(def_config()["buffer"]))
    generate_archive_info(args.message)

    if args.archive_id == None:
        prepare_elf_buffer(args.elfs)

    run_simpoint_args = []
    for spec in app_list(args.spec_app_list,args.spec_apps):
        if args.archive_id == None:
            prepare_rootfs(spec, args.spec_bbl_checkpoint_mode)
            build_spec_bbl(spec)

        if default_config["emulator"]=="QEMU":
            build_bbl_as_gcpt_payload(spec)

        run_simpoint_args.append(spec)

    if args.build_bbl_only:
        exit(0)

    max_threads = 10
    if args.max_threads != None:
        max_threads = int(args.max_threads)

#    for arg in run_simpoint_args:
#        pool.apply_async(run_simpoint,args=(arg,),callback=normal_check,error_callback=err_check)

    pool = Pool(processes=max_threads)
    pool.map_async(run_simpoint, run_simpoint_args, error_callback=err_check)

    time.sleep(3)

    pool.close()
    pool.join()

    for result in get_checkpoint_results():
        per_checkpoint_generate_json(result["profiling_log"], result["cl_res"],
                                     app_list(args.spec_app_list,args.spec_apps),
                                     result["json_path"])
        per_checkpoint_generate_worklist(result["checkpoint_path"],
                                         result["list_path"])

        with open(os.path.join(result["checkpoint_path"], "result"), "w") as f:
            print("{}: {}".format("checkpoint path",
                                  os.path.abspath(result["checkpoint_path"])),
                  file=f)
            print("{}: {}".format("json path",
                                  os.path.abspath(result["json_path"])),
                  file=f)
            print("{}: {}".format("list path",
                                  os.path.abspath(result["list_path"])),
                  file=f)
        print("Execute finish, check result in {}".format(os.path.join(result["checkpoint_path"], "result")))
