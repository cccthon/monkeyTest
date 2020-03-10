import os
import sys
import re
import time
currFile = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.abspath(os.path.join(currFile, "..")))

from wsgiref.validate import validator
from monkey.BasePickle import *
from airtest.core.api import init_device
from airtest.core.api import connect_device
from airtest.core.api import install
from airtest.core.api import start_app
from airtest.core.android.adb import ADB



def connect_dev(devList=[]):
	for dev in devList:
		ADB(dev).disconnect()
		connect_device(f"android:///{dev}")
		print(ADB(dev).get_status())
	devices = [tmp[0] for tmp in ADB().devices(state="device")]
	return devices


def init_dev(devices):
	dev_obj = init_device(platform='Android', uuid=devices)
	return dev_obj

def install_apk(dev_obj,apkPath,package_name):
	#wake up 
	dev_obj.wake()
	dev_obj.home()
	fileList = os.listdir(apkPath)
	ADB(dev_obj.uuid).install_app(f"{apkPath}/{str(fileList[0])}", replace=True, install_options=["-d", "-g"])
	ADB(dev_obj.uuid).start_app(package_name)
	time.sleep(3)  #等待启动首页广告加载完成。   要不然monkey全部点着广告在玩
	# dev_obj.home()


def get_pid(dev_obj, package_name):
	cmd = f'dumpsys activity top |grep "ACTIVITY {package_name}"'
	pid = dev_obj.shell(cmd)
	print("pid: ",pid)
	return pid.split("pid=")[-1].strip("\n")

def get_battery(dev_obj):
	cmd = "dumpsys battery |grep level"
	battery = dev_obj.shell(cmd).split()[-1]
	print(f"battery level - {dev_obj.uuid}: ", battery)
	writeInfo(battery, PATH(f"../info/{dev_obj.uuid}_battery.pickle"))
	return battery

def get_phone_Kernel(dev_obj):
	#({'release': '9', 'phone_name': 'MI 6', 'phone_model': 'Xiaomi'}, 5861796, '8核', '1080x1920')
	model = {}
	pix = dev_obj.shell("wm size").split()[-1]
	model["release"] = dev_obj.shell("getprop ro.build.version.release").strip("\n")
	model["phone_name"] = dev_obj.shell("getprop ro.product.model").strip("\n")
	model["phone_model"] = dev_obj.shell("getprop ro.product.brand").strip("\n")
	men_total = dev_obj.shell("cat /proc/meminfo").split()[1]
	cpu_info = dev_obj.shell("cat /proc/cpuinfo").split()
	cpu_str = ".".join([x for x in cpu_info]) # 转换为string
	cpu_sum = str(len(re.findall("processor", cpu_str)))
	return {"phone": model, "mem": men_total, "cpu_sum": int(cpu_sum), "pix": pix}

def get_mem(dev_obj, pkg_name):
	try:
		cmd = dev_obj.shell(f"dumpsys meminfo {pkg_name} |grep TOTAL")
		mem = cmd.split()[1]
	except:
		mem = 0
	print(mem)
	writeInfo(int(mem), PATH(f"../info/{dev_obj.uuid}_men.pickle"))
	return int(mem)



def get_fps(dev_obj, pkg_name):
	results = dev_obj.shell(f"dumpsys gfxinfo {pkg_name}")
	# print(results)
	frames = [x for x in results.split('\n') if validator(x)]
	frame_count = len(frames)
	jank_count = 0
	vsync_overtime = 0
	render_time = 0
	for frame in frames:
		time_block = re.split(r'\s+', frame.strip())
		if len(time_block) == 3:
			try:
				render_time = float(time_block[0]) + float(time_block[1]) + float(time_block[2])
			except Exception as e:
				render_time = 0

		'''
		当渲染时间大于16.67，按照垂直同步机制，该帧就已经渲染超时
		那么，如果它正好是16.67的整数倍，比如66.68，则它花费了4个垂直同步脉冲，减去本身需要一个，则超时3个
		如果它不是16.67的整数倍，比如67，那么它花费的垂直同步脉冲应向上取整，即5个，减去本身需要一个，即超时4个，可直接算向下取整

		最后的计算方法思路：
		执行一次命令，总共收集到了m帧（理想情况下m=128），但是这m帧里面有些帧渲染超过了16.67毫秒，算一次jank，一旦jank，
		需要用掉额外的垂直同步脉冲。其他的就算没有超过16.67，也按一个脉冲时间来算（理想情况下，一个脉冲就可以渲染完一帧）

		所以FPS的算法可以变为：
		m / （m + 额外的垂直同步脉冲） * 60
		'''
		if render_time > 16.67:
			jank_count += 1
			if render_time % 16.67 == 0:
				vsync_overtime += int(render_time / 16.67) - 1
			else:
				vsync_overtime += int(render_time / 16.67)

	_fps = int(frame_count * 60 / (frame_count + vsync_overtime))
	writeInfo(_fps, PATH(f"../info/{dev_obj.uuid}_fps.pickle"))

	# return (frame_count, jank_count, fps)
	print("-----fps------")
	print(_fps)



def get_flow(dev_obj, pid, netType):
	flow = 0
	if netType == "wifi":
		flow = dev_obj.shell(f"cat /proc/{pid}/net/dev |grep wlan0")
	if netType == "gprs":
		flow = dev_obj.shell(f"cat /proc/{pid}/net/dev |grep rmnet0")
	print(flow)
	upflow = int(flow.split()[1])
	downflow = int(flow.split()[9])
	writeFlowInfo(upflow, downflow, PATH("../info/" + dev_obj.uuid + "_flow.pickle"))


'''
计算某进程的cpu使用率
100*( processCpuTime2 – processCpuTime1) / (totalCpuTime2 – totalCpuTime1) (按100%计算，如果是多核情况下还需乘以cpu的个数);
cpukel cpu几核
pid 进程id
'''
def cpu_rate(dev_obj, pid, cpukel):
	processCpuTime1 = processCpuTime(dev_obj, pid)
	time.sleep(1)
	processCpuTime2 = processCpuTime(dev_obj, pid)
	processCpuTime3 = processCpuTime2 - processCpuTime1

	totalCpuTime1 = totalCpuTime(dev_obj)
	time.sleep(1)
	totalCpuTime2 = totalCpuTime(dev_obj)
	totalCpuTime3 = (totalCpuTime2 - totalCpuTime1)*int(cpukel)
	print("totalCpuTime3="+str(totalCpuTime3))
	print("processCpuTime3="+str(processCpuTime3))

	cpu = 100 * (processCpuTime3) / (totalCpuTime3)
	writeInfo(cpu, PATH(f"../info/{dev_obj.uuid}_cpu.pickle"))
	print("--------cpu--------")
	print(cpu)

'''
每一个进程快照
'''
def processCpuTime(dev_obj, pid):
	'''
	pid     进程号
	utime   该任务在用户态运行的时间，单位为jiffies
	stime   该任务在核心态运行的时间，单位为jiffies
	cutime  所有已死线程在用户态运行的时间，单位为jiffies
	cstime  所有已死在核心态运行的时间，单位为jiffies
	'''
	try:
		stat = dev_obj.shell(f"cat /proc/{pid}/stat")
		result = 0
		for i in stat.split()[13:17]:
			result += int(i)

	except :
		result = 0
	print("processCpuTime: ", result)
	return result


'''
 每一个cpu快照均
'''

def totalCpuTime(dev_obj):
	user=nice=system=idle=iowait=irq=softirq= 0
	'''
	user:从系统启动开始累计到当前时刻，处于用户态的运行时间，不包含 nice值为负进程。
	nice:从系统启动开始累计到当前时刻，nice值为负的进程所占用的CPU时间
	system 从系统启动开始累计到当前时刻，处于核心态的运行时间
	idle 从系统启动开始累计到当前时刻，除IO等待时间以外的其它等待时间
	iowait 从系统启动开始累计到当前时刻，IO等待时间(since 2.5.41)
	irq 从系统启动开始累计到当前时刻，硬中断时间(since 2.6.0-test4)
	softirq 从系统启动开始累计到当前时刻，软中断时间(since 2.6.0-test4)
	stealstolen  这是时间花在其他的操作系统在虚拟环境中运行时（since 2.6.11）
	guest 这是运行时间guest 用户Linux内核的操作系统的控制下的一个虚拟CPU（since 2.6.24）
	'''
	stat = dev_obj.shell("cat /proc/stat |grep 'cpu '")
	cpu = stat.split()[1:8]
	result = 0
	for i in cpu:
		result += int(i)
	return result

 

if __name__ == '__main__':
	dev = "192.168.20.78:5555"
	package = "com.jianshu.jianshu"
	obj = init_dev(dev)
	print(obj)
	install_apk(obj,"../install",package)

	# print(type(obj.uuid),obj.uuid)
	# pid = get_pid(obj, package)
	# print(pid)
	# men = get_mem(obj, package)
	# print(men)

	# fps = get_fps(obj, package)
	# print(fps)
	# flow = get_flow(obj, pid, "wifi")
	# print(flow)
	# cpukel = get_phone_Kernel(obj)["cpu_sum"]
	# print(cpukel)
	# cputime = totalCpuTime(obj)
	# print("totalCpuTime---: ",cputime)
	# pc = processCpuTime(obj, pid)
	# print("processCpuTime---: ",pc)
	# cpurate = cpu_rate(obj, pid, cpukel)
