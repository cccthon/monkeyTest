import os
import time
import datetime
import yaml
import shutil
import xlsxwriter
from addict import Dict

from multiprocessing import Pool

from monkey.BaseFile import OperateFile
from monkey.BasePickle import writeInfo, writeSum, readInfo
from monkey import BaseMonitor
from monkey import BaseReport
from monkey.pyecharts_html import *
# from monkey.BaseWriteReport import report

PATH = lambda p: os.path.abspath(
	os.path.join(os.path.dirname(__file__), p)
)


def yaml_data(file="conf/config.yml"):
	with open(file, "r", encoding='UTF-8') as yaml_file:
		data = yaml.safe_load(yaml_file.read())
	return Dict(data)

configData = yaml_data()
currTime = time.strftime("%Y%m%d%H%M%S", time.localtime())


# 手机信息
def get_phome(dev_obj):
	bg = BaseMonitor.get_phone_Kernel(dev_obj)
	app = {}
	app["phone_name"] = f'{bg["phone"]["phone_name"]}_{bg["phone"]["phone_model"]}_Android{bg["phone"]["release"]}'
	app["pix"] = bg["pix"]
	app["rom"] = bg["mem"]
	app["kel"] = bg["cpu_sum"]
	return app

def mkdirInit(dev_obj, app, data=None):
	# destroy(devices)
	basePath = f"./info/{dev_obj.uuid}_"
	cpu = PATH(f"{basePath}cpu.pickle")
	men = PATH(f"{basePath}men.pickle")
	flow = PATH(f"{basePath}flow.pickle")
	battery = PATH(f"{basePath}battery.pickle")
	fps = PATH(f"{basePath}fps.pickle")
	monkeyLog = PATH(f"{basePath}monkeyLog.pickle")
	app[dev_obj.uuid] = {"cpu": cpu, "men": men, "flow": flow, "battery": battery, "fps": fps, "header": get_phome(dev_obj)}
	print()
	print(app[dev_obj.uuid])
	OperateFile(cpu).mkdir_file()
	OperateFile(men).mkdir_file()
	OperateFile(flow).mkdir_file()
	OperateFile(battery).mkdir_file()
	OperateFile(fps).mkdir_file()
	OperateFile(monkeyLog).mkdir_file()
	OperateFile(PATH("./info/sumInfo.pickle")).mkdir_file() # 用于记录是否已经测试完毕，里面存的是一个整数
	OperateFile(PATH("./info/info.pickle")).mkdir_file() # 用于记录统计结果的信息，是[{}]的形式
	writeSum(0, data, PATH("./info/sumInfo.pickle")) # 初始化记录当前真实连接的设备数

# 开始脚本测试
def start_monkey(cmd, log, currTime,devices):
	# Monkey测试结果日志:monkey_log
	os.popen(cmd)
	print(cmd)

	# Monkey时手机日志,logcat
	logcatname = f"{log}{currTime}_{devices}_logcat.log"
	cmd2 = "adb logcat -d >%s" % (logcatname)
	os.popen(cmd2)

	# "导出traces文件"
	# tracesname = log + r"traces.log"
	tracesname = f"{log}{currTime}_{devices}_traces.log"
	cmd3 = "adb shell cat /data/anr/traces.txt>%s" % tracesname
	os.popen(cmd3)

def report_excel(info):
	if not os.path.exists("./report"):
		os.makedirs("./report")
	if not os.path.exists("./report/monkey"):
		os.makedirs("./report/monkey")
	workbook = xlsxwriter.Workbook(f"./report/monkey/monkeyTestReport_{currTime}.xlsx")
	bo = BaseReport.OperateReport(workbook)
	bo.monitor(info)
	bo.crash()
	bo.analysis(info)
	bo.close()

def report_html():
	dataFile = readInfo("./info/info.pickle")
	data = dataAnalysis(dataFile)
	monkeyLog = monkeyLogAnalysis(data)

	detial = line_detial_grid(cpu=data[1], memory=data[2],
		upFlow=data[3],downFlow=data[4],fps=data[5],battery=data[6])

	tab = Tab()
	tab.add(table_base(data[0]), "汇总信息")
	tab.add(detial,"详细信息")
	tab.add(table_traces(monkeyLog),"日志记录")
	tab.render(f"./report/monkey/monkeyTestReport_{currTime}.html")

def runnerPool():
	if os.path.exists(PATH("./info/")):
		shutil.rmtree(PATH("./info/"))  # 删除持久化目录
	os.makedirs(PATH("./info/"))        # 创建持久化目录
	if not os.path.exists(PATH("./log")):
		os.makedirs(PATH("./log"))
	devices_Pool = []
	devices = BaseMonitor.connect_dev(configData.devList)
	
	if devices:
		for item in range(0, len(devices)):
			_app = {}
			_app["devices"] = devices[item]
			_app["num"] = len(devices)
			devices_Pool.append(_app)
		pool = Pool(len(devices))
		pool.map(start, devices_Pool)
		pool.close()
		pool.join()
	else:
		print("设备不存在")


def start(devicess):
	devices = devicess["devices"]
	print(devices)
	num = devicess["num"]
	app = {}
	dev_obj = BaseMonitor.init_dev(devices)
	BaseMonitor.install_apk(dev_obj,"./install",configData.package_name)
	print(devices, app, num)
	mkdirInit(dev_obj, app, num)


	mc = {}
	# monkey开始测试
	currTime = time.strftime("%Y%m%d%H%M%S", time.localtime())
	mc["log"] = PATH("./log") + "/"
	mc["monkey_log"] = f"{mc['log']}{currTime}_{dev_obj.uuid}_monkey.log"
	mc["cmd"] = configData.cmd + " >> " + mc["monkey_log"]
	start_monkey("adb -s " + dev_obj.uuid + " shell " + mc["cmd"], mc["log"], currTime, dev_obj.uuid)
	time.sleep(1)
	starttime = datetime.datetime.now()
	# pid = BaseMonitor.get_pid(dev_obj, configData.package_name)
	cpu_kel = BaseMonitor.get_phone_Kernel(dev_obj)["cpu_sum"]
	# print(cpu_kel)
	beforeBattery = BaseMonitor.get_battery(dev_obj)


	while True:
		with open(mc["monkey_log"], encoding='utf-8') as monkeylog:
			time.sleep(1)  # 每1秒采集检查一次
			pid = BaseMonitor.get_pid(dev_obj, configData.package_name)
			BaseMonitor.cpu_rate(dev_obj, pid, cpu_kel)
			BaseMonitor.get_mem(dev_obj, configData.package_name)
			BaseMonitor.get_fps(dev_obj, configData.package_name)
			BaseMonitor.get_flow(dev_obj, pid, configData.net)
			BaseMonitor.get_battery(dev_obj)

			if monkeylog.read().count('Monkey finished') > 0:
				endtime = datetime.datetime.now()
				print(str(devices)+"测试完成咯")
				writeSum(1, path=PATH("./info/sumInfo.pickle"))
				app[devices] ["header"]["beforeBattery"] = beforeBattery
				app[devices]["header"]["afterBattery"] = BaseMonitor.get_battery(dev_obj)
				app[devices]["header"]["net"] = configData.net
				app[devices]["header"]["monkey_log"] = mc["monkey_log"]
				app[devices]["header"]["time"] = str((endtime - starttime).seconds)
				basePath = f"./info/{dev_obj.uuid}_"
				monkeyLog = PATH(f"{basePath}monkeyLog.pickle")
				app[devices]["monkeyLog"] = monkeyLog
				writeInfo(app, PATH("./info/info.pickle"))
				break
					# go.info[devices]["header"]["sumTime"] = str((endtime - starttime).seconds) + "秒"
					# report(go.info)
	if readInfo(PATH("./info/sumInfo.pickle")) <= 0:
		print(readInfo(PATH("./info/info.pickle")))
		report_excel(readInfo(PATH("./info/info.pickle")))
		


if __name__ == '__main__':
	runnerPool()
	report_html()


