import os
from pyecharts.charts import Bar
import pickle
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from pyecharts.charts import Bar, Tab, Pie, Line, Page, Grid
from pyecharts import options as opts
from pyecharts.faker import Faker, Collector
C = Collector()


def readInfo(path):
	data = []
	with open(path, 'rb') as f:
		try:
			data = pickle.load(f)
			# print(data)
		except EOFError:
			data = []
			# print("读取文件错误")
	print("------read-------")
	print(path)
	print(data)
	return data

def flowAnalysis(flow):
	_flowUp = []
	_flowDown = []
	for i in range(len(flow[0])):
		if i + 1 == len(flow[0]):
			break
		_flowUp.append((flow[0][i + 1] - flow[0][i]) / 1024)

	for i in range(len(flow[1])):
		if i + 1 == len(flow[1]):
			break
		_flowDown.append((flow[1][i + 1] - flow[1][i]) / 1024)

	maxUpFlow = round(max(_flowUp), 2)
	maxDownFlow = round(max(_flowDown), 2)
	avgUpFlow = sum(_flowUp) / len(_flowUp)
	avgDownFlow = sum(_flowDown) / len(_flowDown)
	return {
	"maxUpFlow": maxUpFlow, 
	"maxDownFlow": maxDownFlow,
	"avgUpFlow": avgUpFlow,
	"avgDownFlow": avgDownFlow,
	"upFlowList": _flowUp,
	"downFlowList": _flowDown
	}

def monkeyLogAnalysis(data):
	res = []
	for i in list(set(data[7][0])):
		res.append([ i.split()[0], i.split()[1:-1],  data[7][0].count(i)])
	return res

def dataAnalysis(data):
	dev_row = []
	cpuList = {}
	memList = {}
	upFlowList = {}
	downFlowList = {}
	fpsList = {}
	batteryList = {}

	for devs in data:
		# print(devs.keys())
		for dev in devs:
			d = devs[dev]["header"]

			cpu = readInfo(devs[dev]["cpu"])
			print("cpufffffffffffff: ",cpu)
			maxCpu = round(max(cpu) * 10, 2)
			# print(maxCpu)
			avgCpu = round(sum(cpu) / len(cpu) * 10, 2)
			# print(avgCpu)

			mem = readInfo(devs[dev]["men"])
			print("memoryfffffffffffff: ",mem)
			maxmem = round(max(mem) / 1024, 2)
			# print(maxmem)
			avgmem = round((sum(mem) / len(mem)) / 1024, 2)
			# print(avgmem)

			fps = readInfo(devs[dev]["fps"])
			print("fpsssssssssfffffffffffff: ",fps)
			maxfps = round(max(fps), 2)
			# print(maxfps)
			avgfps = round(sum(fps) / len(fps), 2)
			# print(avgfps)

			flowFile = readInfo(devs[dev]["flow"])
			print("flow. fffffffffffff: ",flowFile)
			flow = flowAnalysis(flowFile)
			# print(flow)

			batteryFile = readInfo(devs[dev]["battery"])
			monkeyLogFile = readInfo(devs[dev]["monkeyLog"])

			dev_row.append([d["phone_name"], dev, str(d["kel"])+"核", d["rom"], d["pix"], d["net"], d["time"], 
				str(round(maxCpu, 2))+"%", str(round(avgCpu, 2))+"%", str(round(maxmem, 0))+"M", 
				str(round(avgmem, 0))+"M", round(maxfps, 0), round(avgfps, 0), d["beforeBattery"]+"%", d["afterBattery"]+"%", 
				str(round(flow["maxUpFlow"], 0))+"KB", str(round(flow["avgUpFlow"], 0))+"KB", 
				str(round(flow["maxDownFlow"], 0))+"KB", str(round(flow["avgDownFlow"], 0))+"KB"])
			
			cpuList[d["phone_name"]] = cpu
			memList[d["phone_name"]] = mem
			upFlowList[d["phone_name"]] = flowFile[0]
			downFlowList[d["phone_name"]] = flowFile[1]
			fpsList[d["phone_name"]] = fps
			batteryList[d["phone_name"]] = batteryFile

	return dev_row, cpuList, memList, upFlowList, downFlowList, fpsList, batteryList, monkeyLogFile

def table_base(rows) -> Table:
	table = Table()
	headers = ["设备名", "设备号", "CPU", "总内存", "分辨率", "网络", "耗时(s)", "CPU峰值", "CPU均值", "内存峰值", "内存均值", 
	"fps峰值", "fps均值", "开始电量", "结束电量", "上行流量峰值", "上行流量均值", "下行流量峰值", "下行流量均值"]
	table.add(headers, rows).set_global_opts(
		title_opts=ComponentTitleOpts(title="手机汇总信息", subtitle="")
	)
	return table

def table_traces(rows) -> Table:
	table = Table()
	headers = ["设备名", "MonkeyError", "条数"]
	table.add(headers, rows).set_global_opts(
		title_opts=ComponentTitleOpts(title="错误日志收集")
	)
	return table

def line_cpu(cpu) -> Line:
	step = list(range(1, max([len(cpu[i])*2 for i in cpu]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)

	for dev in cpu:
		line.add_yaxis(
			dev,
			list(map(lambda x: round(x * 10, 2), cpu[dev])),
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="CPU(%)", pos_top="2%"))
	return line

def line_memory(mem) -> Line:
	step = list(range(1, max([len(mem[i])*2 for i in mem]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)

	for dev in mem:
		line.add_yaxis(
			dev,
			list(map(lambda x: round(x / 1024, 0), mem[dev])),
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="Memory(M)", pos_top="15%"))
	return line

def line_upflow(upFlow) -> Line:
	step = list(range(1, max([len(upFlow[i])*2 for i in upFlow]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)
	for dev in upFlow:
		_flowUp = []
		for i in range(len(upFlow[dev])):
			if i + 1 == len(upFlow[dev]):
				break
			_flowUp.append(round((upFlow[dev][i + 1] - upFlow[dev][i]) / 1024,0))
		print(_flowUp)
		line.add_yaxis(
			dev,
			_flowUp,
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="上行流量(KB)", pos_top="28%"))
	return line

def line_downflow(downFlow) -> Line:
	step = list(range(1, max([len(downFlow[i])*2 for i in downFlow]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)
	for dev in downFlow:
		_downFlow = []
		for i in range(len(downFlow[dev])):
			if i + 1 == len(downFlow[dev]):
				break
			_downFlow.append(round((downFlow[dev][i + 1] - downFlow[dev][i]) / 1024,0))
		print(_downFlow)
		line.add_yaxis(
			dev,
			_downFlow,
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="下行流量(KB)", pos_top="41%"))
	return line

def line_fps(fps) -> Line:
	step = list(range(1, max([len(fps[i])*2 for i in fps]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)
	for dev in fps:
		line.add_yaxis(
			dev,
			list(map(lambda x: round(x , 0), fps[dev])),
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="FPS", pos_top="54%"))
	return line

def line_battery(battery) -> Line:
	step = list(range(1, max([len(battery[i])*2 for i in battery]), 2))
	line = Line(init_opts=opts.InitOpts(width="1000px", height="800px"))
	line.add_xaxis(step)
	for dev in battery:
		line.add_yaxis(
			dev,
			list(map(lambda x: x, battery[dev])),
			markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="min")]),
		)
	line.set_global_opts(title_opts=opts.TitleOpts(title="battery", pos_top="67%"))
	return line

def line_detial_grid(cpu,memory,upFlow,downFlow,fps,battery) -> Grid:
	line1 = line_cpu(cpu)
	line2 = line_memory(memory)
	line3 = line_upflow(upFlow)
	line4 = line_downflow(downFlow)
	line5 = line_fps(fps)
	line6 = line_battery(battery)

	grid = (
		Grid(init_opts=opts.InitOpts(width="1400px", height="3000px"))
		.add(line1, grid_opts=opts.GridOpts(pos_top="2%", height="10%"))
		.add(line2, grid_opts=opts.GridOpts(pos_top="15%", height="10%"))
		.add(line3, grid_opts=opts.GridOpts(pos_top="28%", height="10%"))
		.add(line4, grid_opts=opts.GridOpts(pos_top="41%", height="10%"))
		.add(line5, grid_opts=opts.GridOpts(pos_top="54%", height="10%"))
		.add(line6, grid_opts=opts.GridOpts(pos_top="67%", height="10%"))
	)
	return grid



def line_detial_page(cpu,memory,upFlow,downFlow,fps,battery) -> Page:
	line1 = line_cpu(cpu)
	line2 = line_memory(memory)
	line3 = line_upflow(upFlow)

	table1 = table_base(data[0])

	page = (
		Page()
		.add(table1)
	)
	return page


if __name__ == '__main__':

	print("----"*20)
	dataFile = readInfo("../info/info.pickle")
	data = dataAnalysis(dataFile)
	monkeyLog = monkeyLogAnalysis(data)

	detial = line_detial_grid(cpu=data[1], memory=data[2],
		upFlow=data[3],downFlow=data[4],fps=data[5],battery=data[6])

	tab = Tab()
	tab.add(table_base(data[0]), "汇总信息")
	tab.add(detial,"详细信息")
	tab.add(table_traces(monkeyLog),"日志记录")
	tab.render()



