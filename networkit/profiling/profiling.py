#
# file: profiling.py
# author: Mark Erb
#

from networkit import *

from . import multiprocessing
from . import stat
from . import plot

from IPython.core.display import *
import collections


def readfile(postfix):
	""" private helper function: profiling-meta-file to string (all whitespace characters are replaced by ' ') """
	with open(__file__[:__file__.rfind(".py")] + "." + postfix, "r") as file:
		return " ".join(file.read().split())

		
try:
	__IPYTHON__
	
	def _initHeader(tag, type, data):
		""" private helper function for notebook hack: create content of extended header """
		result = """
			{
				var element = document.getElementById('NetworKit_""" + tag + """');
				if (element) {
					element.parentNode.removeChild(element);
				}
				element = document.createElement('""" + tag + """');
				element.type = 'text/""" + type + """';
				element.innerHTML = '""" + data + """';
				element.setAttribute('id', 'NetworKit_""" + tag + """');
				document.head.appendChild(element);
			}
		"""
		return result

		
	def _initOverlay(name, data):
		""" private helper function for notebook hack: create content of overlay """
		result = """
			{
				var element = document.getElementById('NetworKit_""" + name + """');
				if (element) {
					element.parentNode.removeChild(element);
				}
				element = document.createElement('div');
				element.innerHTML = '<div id="NetworKit_""" + name + """_Toolbar_Top"><div class="button icon-close" id="NetworKit_""" + name + """_Close" /></div>""" + data + """';
				element.setAttribute('id', 'NetworKit_""" + name + """');
				document.body.appendChild(element);
				document.getElementById('NetworKit_""" + name + """_Close').onclick = function (e) {
					document.getElementById('NetworKit_""" + name + """').style.display = 'none';
				}
			}
		"""
		return result

		
	display_html(
		HTML("""
			<script type="text/javascript">
			<!--
				""" + _initHeader("script", "javascript", readfile("js"))  + """
				""" + _initHeader("style",  "css",        readfile("css")) + """
				""" + _initOverlay("Overlay", readfile("overlay.html")) + """
			-->
			</script>
		""")
	)
except Exception as e:
	print(str(e))
	

class Profile:
	""" TODO: """
	__TOKEN = object();
	__pageCount = 0
	__verbose = False
	__verboseLevel = 0
	__parallel = multiprocessing.numberOfProcessors() * 2


	def __init__(self, G, token=object()):
		""" TODO: """
		if token is not self.__TOKEN:
			raise ValueError("call create(G) to create an instance")
		self.__G = G
		self.__properties = {}
		self.__measures = collections.OrderedDict()
		self.__correlations = {}


	@classmethod
	def create(cls, G, exclude=["KPathCentrality", "KatzCentrality"]):
		""" TODO: """
		result = cls(G, cls.__TOKEN)

		def funcScores(instance):
			return instance.scores()

		def funcSizes(instance):
			return sorted(instance.getPartition().subsetSizes())

		if G.isDirected():
			classConnectedComponents = properties.StronglyConnectedComponents
		else:
			classConnectedComponents = properties.ConnectedComponents

		for parameter in [
			("Node Centrality",	"Degree Centrality",			True,	funcScores,	"Score",	centrality.DegreeCentrality, 			(G, )),
			("Node Centrality",	"K-Core Decomposition",			True,	funcScores,	"Score",	centrality.CoreDecomposition, 			(G, )),
			("Node Centrality",	"Local Clustering Coefficient",	True,	funcScores,	"Score",	centrality.LocalClusteringCoefficient,	(G, )),
			("Node Centrality",	"Page Rank",					True,	funcScores,	"Score",	centrality.PageRank, 					(G, )),
			("Node Centrality",	"K-Path Centrality",			True,	funcScores,	"Score",	centrality.KPathCentrality,				(G, )),
			("Node Centrality",	"Katz Centrality",				True,	funcScores,	"Score",	centrality.KatzCentrality,				(G, )),
			("Node Centrality",	"Betweenness",					True,	funcScores,	"Score",	centrality.ApproxBetweenness2,			(G, max(42, G.numberOfNodes() / 10000), False)),
		#	("Partition",		"Community",					False,	funcSizes,	"Nodes Per Community",	community.LPDegreeOrdered, 				(G, )),
		#	("Partition",		"Community",					False,	funcSizes,	"Nodes Per Community",	community.PLP, 							(G, )),
			("Partition",		"Community",					False,	funcSizes,	"Nodes Per Community",	community.PLM, 							(G, )),
			("Partition",		"Connected Components",			False,	funcSizes,	"Connected Nodes",	classConnectedComponents,				(G, ))
		]: result.__addMeasure(parameter, exclude)

		result.__loadProperties()
		result.__loadMeasures()
		return result;


	@classmethod
	def setVerbose(cls, verbose=False, level=0):
		""" TODO: """
		cls.__verbose = verbose
		cls.__verboseLevel = level


	@classmethod
	def getVerbose(cls):
		""" TODO: """
		return (cls.__verbose, cls.__verboseLevel)


	@classmethod
	def setParallel(cls, parallel):
		""" TODO: """
		if (parallel < 1):
			raise ValueError("parallel < 1");
		cls.__parallel = parallel


	@classmethod
	def getParallel(cls):
		""" TODO: """
		return cls.__parallel


	def getStat(self, measure):
		""" TODO: """
		return self.__measures[measure]["stat"]


	def getCategory(self, measure):
		""" TODO: """
		return self.__measures[measure]["category"]


	def getElapsedTime(self, measure):
		""" TODO: """
		return self.__measures[measure]["time"]


	def show(self, style="light", color=(0, 0, 1)):
		""" TODO: """
		try:
			__IPYTHON__
		except:
			raise RuntimeError("this function cannot be used outside ipython notebook")
			
		if self.__verbose:
			timerAll = stopwatch.Timer()
			
		theme = plot.Theme()
		theme.set(style, color)
		
		pool = multiprocessing.ThreadPool(self.__parallel)
		for name in self.__measures:
			category = self.__measures[name]["category"]
			pool.put(
				plot.Measure(name, (
					0,
					self.__measures[name]["stat"],
					self.__measures[name]["label"],
					theme
				))
			)
			pool.put(
				plot.Measure(name, (
					1,
					self.__measures[name]["stat"],
					self.__measures[name]["label"],
					theme
				))
			)				
			if category == "Partition":
				pool.put(
					plot.Measure(name, (
						2,
						self.__measures[name]["stat"],
						self.__measures[name]["label"],
						theme
					))
				)
		while pool.numberOfTasks() > 0:
			(type, name, data) = pool.get()
			try:
				category = self.__measures[name]["category"]
				
				if type == "Plot.Measure":
					(index, image) = data
					self.__measures[name]["image"][index] = image
			except:
				pass
		pool.join()

		templateMeasure = readfile("measure.html")

		results = {}
		for category in self.__correlations:
			results[category] = {}
			results[category]["Correlations"] = {}
			results[category]["Correlations"]["HeatMaps"] = ""
			results[category]["Correlations"]["ScatterPlots"] = ""
			results[category]["Measures"] = ""
			results[category]["Overview"] = ""

			def funcHeatMap(category, correlationName):
				result = "<div class=\"SubCategory HeatTable\" data-title=\"" + correlationName + "\">"
				keyBList = []
				for keyA in self.__measures:
					if self.__measures[keyA]["category"] == category and self.__measures[keyA]["correlate"]:
						keyBList.append(keyA)
						for keyB in keyBList:
							try:
								value = self.__correlations[category][keyA][keyB]
							except:
								value = self.__correlations[category][keyB][keyA]
							result += "<div class=\"HeatCell\" title=\"" + keyB + " - " + keyA + "\" data-image=\"data:image/svg+xml;utf8," + value["image"] + "\" data-heat=\"{:+.3F}\"></div>".format(value["stat"][correlationName])
						result += "<div class=\"HeatCellName\">" + keyB + "</div><br>"
				result += "</div>"
				return result
			results[category]["Correlations"]["HeatMaps"] += funcHeatMap(category, "Pearson's Correlation Coefficient")
			results[category]["Correlations"]["HeatMaps"] += funcHeatMap(category, "Spearman's Rang Correlation Coefficient")
			results[category]["Correlations"]["HeatMaps"] += funcHeatMap(category, "Fechner's Correlation Coefficient")

			def funcScatterPlot(category):
				result = ""
				keyBList = []
				for keyA in self.__measures:
					if self.__measures[keyA]["category"] == category and self.__measures[keyA]["correlate"]:
						keyBList.append(keyA)
						for keyB in keyBList:
							if keyA != keyB:
								try:
									value = self.__correlations[category][keyA][keyB]
								except:
									value = self.__correlations[category][keyB][keyA]
								result += "<div class=\"Thumbnail_ScatterPlot\" data-title=\"" + keyB + "\" data-title-second=\"" + keyA + "\"><img src=\"data:image/svg+xml;utf8," + value["image"] + "\" /></div>"
				return result
			results[category]["Correlations"]["ScatterPlots"] += funcScatterPlot(category)

		for key in self.__measures:
			measure = self.__measures[key]
			name = measure["name"]
			category = measure["category"]
			image = measure["image"]
			stat = measure["stat"]
			
			try:
				with open(__file__[:__file__.rfind("/")] + "/description/" + key + ".txt") as file:
					description = file.read()
			except: 
				# description = measure["class"].__doc__
				description = "N/A"
			
			try:
				extentions = "<div class=\"PartitionPie\"><img src=\"data:image/svg+xml;utf8," + image[2] + "\" /></div>"
			except:
				extentions = ""
			
			results[category]["Measures"] += self.__formatMeasureTemplate(
				templateMeasure,
				key,
				name,
				image,
				stat,
				extentions,
				description
			)
			results[category]["Overview"] += "<div class=\"Thumbnail_Overview\" data-title=\"" + key + "\"><a href=\"#NetworKit_Page_" + str(self.__pageCount) + "_" + key + "\"><img src=\"data:image/svg+xml;utf8," + image[1] + "\" /></a></div>"

		templateProfile = readfile("profile.html")
		result = self.__formatProfileTemplate(
			templateProfile,
			results
		)
		display_html(HTML(result))
		self.__pageCount = self.__pageCount + 1

		if self.__verbose:
			print("\ntotal time: {:.2F} s".format(timerAll.elapsed))


	def __formatMeasureTemplate(self, template, key, name, image, stat, extentions, description):
		""" TODO: """
		pageIndex = self.__pageCount
		result = template.format(**locals())
		return result


	def __formatProfileTemplate(self, template, results):
		""" TODO: """
		pageIndex = self.__pageCount
		properties = self.__properties
		result = template.format(**locals())
		return result


	def __addMeasure(self, args, exclude):
		""" TODO: """
		(measureCategory, measureName, correlate, getter, label, measureClass, parameters) = args
		measureKey = measureClass.__name__
		if measureKey not in exclude:
			measure = {}
			measure["name"] = measureName
			measure["category"] = measureCategory
			measure["correlate"] = correlate
			measure["getter"] = getter
			measure["label"] = label
			measure["class"] = measureClass
			measure["parameters"] = parameters
			measure["data"] = {}
			measure["image"] = {}
			self.__measures[measureKey] = measure
		try:
			self.__correlations[measureCategory]
		except:
			self.__correlations[measureCategory] = {}


	def __loadProperties(self):
		""" TODO: """
		self.__properties["Nodes"] = self.__G.numberOfNodes()
		self.__properties["Edges"] = self.__G.numberOfEdges()
		self.__properties["Directed"] = self.__G.isDirected()
		self.__properties["Weighted"] = self.__G.isWeighted()
		self.__properties["Density"] = properties.density(self.__G)
		self.__properties["Diameter Range"] = properties.Diameter.estimatedDiameterRange(self.__G, error=0.1)


	def __loadMeasures(self):
		""" TODO: """
		def funcPrint(str):
			if self.__verbose:
				if self.__verboseLevel >= 1:
					print(str, flush=True)
				else:
					print(".", end="", flush=True)

		pool = multiprocessing.ThreadPool(self.__parallel)

		if self.__verbose:
			timerAll = stopwatch.Timer()

		for name in self.__measures:
			measure = self.__measures[name]
			instance = measure["class"](*measure["parameters"])
			if self.__verbose:
				print(name + ": ", end="", flush=True)
			timerInstance = stopwatch.Timer()
			instance.run()
			elapsed = timerInstance.elapsed
			if self.__verbose:
				print("{:.2F} s".format(elapsed), flush=True)
			measure["data"]["sample"] = measure["getter"](instance)
			measure["data"]["sorted"] = stat.sorted(measure["data"]["sample"])
			measure["data"]["ranged"] = stat.ranged(measure["data"]["sample"])
			measure["time"] = elapsed

		if self.__verbose:
			print("")

		for name in self.__measures:
			if len(self.__measures[name]["data"]["sample"]) <= 1:
				del self.__measures[name]
			else:
				category = self.__measures[name]["category"]
				pool.put(
					stat.Stat(name, (
						self.__measures[name]["data"]["sample"],
						self.__measures[name]["data"]["sorted"],
						self.__measures[name]["data"]["ranged"],
						category == "Partition"
					))
				)
		while pool.numberOfTasks() > 0:
			(type, name, data) = pool.get()
			
			try:
				category = self.__measures[name]["category"]

				if type == "Stat":
					self.__measures[name]["stat"] = data
					funcPrint("Stat: " + name)					
					if self.__measures[name]["correlate"]:
						for key in self.__correlations[category]:
							self.__correlations[category][key][name] = {}
							self.__correlations[category][key][name]["stat"] = {}
							pool.put(
								stat.Correlation(key, (
									name,
									self.__measures[key]["data"]["sample"],
									self.__measures[key]["data"]["ranged"],
									self.__measures[key]["stat"],
									self.__measures[name]["data"]["sample"],
									self.__measures[name]["data"]["ranged"],
									self.__measures[name]["stat"]
								))
							)
							pool.put(
								plot.Scatter(key, (
									name,
									self.__measures[key]["data"]["sample"],
									self.__measures[name]["data"]["sample"]
								))
							)
						self.__correlations[category][name] = {}
						self.__correlations[category][name][name] = {}
						self.__correlations[category][name][name]["stat"] = {
							"Spearman's Rang Correlation Coefficient": 1,
							"Pearson's Correlation Coefficient": 1,
							"Fechner's Correlation Coefficient": 1
						}
						self.__correlations[category][name][name]["image"] = ""

				elif type == "Correlation":
					(nameB, correlation) = data
					funcPrint("Correlation: " + name + " <-> " + nameB)
					self.__correlations[category][name][nameB]["stat"] = correlation

				elif type == "Plot.Scatter":
					(nameB, image) = data
					funcPrint("Plot.Scatter: " + name)
					self.__correlations[category][name][nameB]["image"] = image
			except:
				pass
		pool.join()

		if self.__verbose:
			if self.__verboseLevel < 1:
				print("")
			print("\ntotal time (measures + stats + correlations): {:.2F} s".format(timerAll.elapsed))