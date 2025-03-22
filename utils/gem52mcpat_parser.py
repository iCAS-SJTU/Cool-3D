# Revised from:
# 1. https://github.com/saideeptiku/Gem5McPatParser/blob/master/Gem5McPATParser.py
# 2. https://github.com/Hardik44/Gem5toMcPat_parser/blob/master/Program.py


"""
[usage]:
python3 gem52mcpat-parser.py -c config.json -s stats.txt -t ./template_parser.xml

[formatting]:
"black-formatter.args": [
        "--line-length=110"
]

[testing environment]:
python 3.6.9
python 3.8.5
python 3.13

"""

import argparse
import sys
import json
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom
import copy
import types
import logging
from math import log2

logging.basicConfig(level=logging.WARNING) #logging.DEBUG for debugging


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def create_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Gem5 to McPAT parser",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        required=True,
        metavar="PATH",
        help="Input config.json from Gem5 output.",
    )
    parser.add_argument(
        "--stats",
        "-s",
        type=str,
        required=True,
        metavar="PATH",
        help="Input stats.txt from Gem5 output.",
    )
    parser.add_argument(
        "--template",
        "-t",
        type=str,
        required=True,
        metavar="PATH",
        help="Template XML file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=argparse.FileType("w"),
        default="mcpat_in.xml",
        metavar="PATH",
        help="Output file for McPAT input in XML format (default: mcpat-in.xml)",
    )

    return parser


class PIParser(ET.TreeBuilder):
    def __init__(self, *args, **kwargs):
        # call init of superclass and pass args and kwargs
        super(PIParser, self).__init__(*args, **kwargs)

        self.CommentHandler = self.comment
        self.ProcessingInstructionHandler = self.pi
        self.start("document", {})

    def close(self):
        self.end("document")
        return ET.TreeBuilder.close(self)

    def comment(self, data):
        self.start(ET.Comment, {})
        self.data(data)
        self.end(ET.Comment)

    def pi(self, target, data):
        self.start(ET.PI, {})
        self.data(target + " " + data)
        self.end(ET.PI)


def parse(source):
    parser = ET.XMLParser(target=PIParser())
    return ET.parse(source, parser=parser)


def readStatsFile(statsFile):
    global stats
    stats = {}
    F = open(statsFile)
    ignores = re.compile(r"^---|^$")
    statLine = re.compile(
        r"([a-zA-Z0-9_\.:-]+)\s+([-+]?[0-9]+\.[0-9]+|[-+]?[0-9]+|nan|inf)"
    )
    count = 0
    for line in F:
        # ignore empty lines and lines starting with "---"
        if not ignores.match(line):
            count += 1
            match = statLine.match(line)
            if match:
                statKind = match.group(1)
                statValue = match.group(2)
                if statValue == "nan":
                    logging.warning("%s is nan. Setting it to 0" % statKind)
                    statValue = "0"
                stats[statKind] = statValue
            else:
                logging.warning(
                    f"Line {count} did not match the expected format: {line.strip()}"
                )
    F.close()


def readConfigFile(configFile):
    global config
    F = open(configFile)
    config = json.load(F)
    # print(type(config))
    F.close()


def readMcpatFile(templateFile):
    global templateMcpat
    templateMcpat = parse(templateFile)
    # ET.dump(templateMcpat)


def prepareTemplate(outputFile):
    numCores = len(config["system"]["cpu"])
    logging.debug("Number of CPU cores: %d" % numCores)
    privateL2 = "l2" in config["system"]["cpu"][0].keys()
    logging.debug("Private L2: %s" % privateL2)
    sharedL2 = "l2" in config["system"].keys()
    logging.debug("Shared L2: %s" % sharedL2)

    if privateL2:
        numL2 = numCores
    elif sharedL2:
        numL2 = 1
    else:
        numL2 = 0

    numL3 = 0  # TODO: complete

    logging.debug("Number of L2 caches: %d" % numL2)

    targetCoreClockrate = int(
        10**6 / config["system"]["cpu_clk_domain"]["clock"][0]
    )
    logging.debug("Target core clock rate: %d" % targetCoreClockrate)

    if numCores == 1:
        try:
            totalCycles = int(stats["system.cpu.numCycles"])
        except KeyError:
            logging.warning("No total cycles found in stats.txt. Setting to 0")
        try:
            idleCycles = int(stats["system.cpu.idleCycles"])
        except KeyError:
            logging.warning("No idle cycles found in stats.txt. Setting to 0")
    else:
        totalCycles = 0
        idleCycles = 0
        for coreCounter in range(numCores):
            path = "system.cpu" + str(coreCounter) + ".numCycles"
            try:
                totalCycles += int(stats[path])
            except KeyError:
                logging.warning(
                    "No total cycles found in stats.txt for core %d. Setting to 0"
                    % coreCounter
                )
                totalCycles += 0
            path = "system.cpu" + str(coreCounter) + ".idleCycles"
            try:
                idleCycles += int(stats[path])
            except KeyError:
                logging.warning(
                    "No idle cycles found in stats.txt for core %d. Setting to 0"
                    % coreCounter
                )
                idleCycles += 0

    logging.debug("Total cycles: %d" % totalCycles)
    logging.debug("Idle cycles: %d" % idleCycles)

    elemCounter = 0
    root = templateMcpat.getroot()

    if len(root) == 0 or len(root[0]) == 0:
        logging.error("Template file is empty")
        sys.exit(1)

    children_to_remove = []

    for child in root[0][0]:
        elemCounter += 1  # to add elements in correct sequence

        if child.attrib.get("name") == "number_of_cores":
            child.attrib["value"] = str(numCores)
        if child.attrib.get("name") == "number_of_L2s":
            child.attrib["value"] = str(numL2)
        if child.attrib.get("name") == "Private_L2":
            if numL2 == 0:
                Private_L2 = str(0)
            elif sharedL2:
                Private_L2 = str(0)
            else:
                Private_L2 = str(1)
            child.attrib["value"] = Private_L2
        if child.attrib.get("name") == "total_cycles":
            child.attrib["value"] = str(totalCycles)
        if child.attrib.get("name") == "idle_cycles":
            child.attrib["value"] = str(idleCycles)
        if child.attrib.get("name") == "busy_cycles":
            child.attrib["value"] = str(totalCycles - idleCycles)
        if child.attrib.get("name") == "target_core_clockrate":
            child.attrib["value"] = str(targetCoreClockrate)

        temp = child.attrib.get("value")

        # start with <component id="system.core0" name="core0">
        # remove a core template element and replace it with number of cores template elements
        if child.attrib.get("name") == "core":
            coreElem = copy.deepcopy(child)

            coreElemCopy = copy.deepcopy(coreElem)
            for coreCounter in range(numCores):
                coreElem.attrib["name"] = "core" + str(coreCounter)
                coreElem.attrib["id"] = "system.core" + str(coreCounter)

                IFUDutyCycle = 0
                LSUDutyCycle = 0
                IntDutyCycle = 0
                MULDutyCycle = 0
                FPUDutyCycle = 0
                LSUCnt = 0
                ALUPerCore = 0
                MULPerCore = 0
                FPUPerCore = 0
                for FU in config["system"]["cpu"][coreCounter]["fuPool"][
                    "FUList"
                ]:
                    for OP in FU["opList"]:
                        if OP["opClass"] == "IntAlu":
                            ALUPerCore += float(
                                FU["count"] / len(FU["opList"])
                            )
                        if OP["opClass"] == "IprAccess":
                            if OP["pipelined"] == False:
                                IFUDutyCycle += float(1 / (OP["opLat"])) / len(
                                    FU["opList"]
                                )
                                logging.debug(
                                    "IFU Duty Cycle: %f" % IFUDutyCycle
                                )
                            else:
                                IFUDutyCycle += float(1) / len(FU["opList"])

                                logging.debug(
                                    "IFU Duty Cycle: %f" % IFUDutyCycle
                                )
                        if (
                            OP["opClass"] == "MemRead"
                            or OP["opClass"] == "MemWrite"
                            or OP["opClass"] == "FloatMemRead"
                            or OP["opClass"] == "FloatMemWrite"
                        ):
                            if OP["pipelined"] == False:
                                LSUDutyCycle += float(1 / (OP["opLat"])) / 4
                            else:
                                LSUDutyCycle += float(1) / 4
                            LSUDutyCycle = min(LSUDutyCycle, float(1))
                            logging.debug("LSU Duty Cycle: %f" % LSUDutyCycle)
                        if OP["opClass"] == "IntAlu":
                            if OP["pipelined"] == False:
                                IntDutyCycle += float(1 / (OP["opLat"])) / len(
                                    FU["opList"]
                                )
                            else:
                                IntDutyCycle += float(1) / len(FU["opList"])
                            logging.debug("ALU Duty Cycle: %f" % IntDutyCycle)
                        if (
                            OP["opClass"] == "IntMult"
                            or OP["opClass"] == "IntDiv"
                        ):
                            MULPerCore += float(
                                FU["count"] / len(FU["opList"])
                            )
                            if OP["pipelined"] == False:
                                MULDutyCycle += float(1 / (OP["opLat"])) / 2
                            else:
                                MULDutyCycle += float(1) / 2
                            logging.debug("Mult Duty Cycle: %f" % MULDutyCycle)
                        if (
                            OP["opClass"] == "FloatAdd"
                            or OP["opClass"] == "FloatCmp"
                            or OP["opClass"] == "FloatCvt"
                            or OP["opClass"] == "FloatMult"
                            or OP["opClass"] == "FloatDiv"
                            or OP["opClass"] == "FloatSqrt"
                            or OP["opClass"] == "FloatMultAcc"
                            or OP["opClass"] == "FloatMisc"
                        ):
                            FPUPerCore += float(
                                FU["count"] / len(FU["opList"])
                            )
                            if OP["pipelined"] == False:
                                FPUDutyCycle += float(1 / (OP["opLat"])) / 8
                            else:
                                FPUDutyCycle += float(1) / 8
                            logging.debug("FPU Duty Cycle: %f" % FPUDutyCycle)

                MemManUIDutyCycle = IFUDutyCycle
                MemManUDDutyeCycle = LSUDutyCycle

                for coreChild in coreElem:
                    childId = coreChild.attrib.get("id")
                    childValue = coreChild.attrib.get("value")
                    childName = coreChild.attrib.get("name")
                    if (
                        isinstance(childName, str)
                        and childName == "peak_issue_width"
                    ):
                        peakIssueWidth = config["system"]["cpu"][coreCounter][
                            "issueWidth"
                        ]
                        logging.debug("Peak issue width: %d" % peakIssueWidth)
                        childValue = str(peakIssueWidth)
                    if (
                        isinstance(childName, str)
                        and childName == "machine_type"
                    ):
                        if (
                            "O3"
                            in config["system"]["cpu"][coreCounter]["type"]
                        ):
                            childValue = "0"
                        else:
                            childValue = "1"
                        logging.debug("Machine type: %s" % childValue)
                    if isinstance(childName, str) and childName == "x86":
                        if (
                            config["system"]["cpu"][coreCounter]["isa"][0][
                                "type"
                            ]
                            == "X86ISA"
                        ):
                            childValue = "1"
                        else:
                            childValue = "0"
                        archType = config["system"]["cpu"][coreCounter]["isa"][
                            0
                        ]["type"][:3]
                        logging.debug("Arch type: %s" % archType)
                        if archType == "X86":
                            INT_EXE = 2
                            FP_EXE = 8
                        elif archType == "ARM":
                            INT_EXE = 3
                            FP_EXE = 7
                        else:
                            INT_EXE = 3
                            FP_EXE = 6
                    if (
                        isinstance(childName, str)
                        and childName == "pipeline_depth"
                    ):
                        try:
                            base = (
                                config["system"]["cpu"][coreCounter][
                                    "fetchToDecodeDelay"
                                ]
                                + config["system"]["cpu"][coreCounter][
                                    "decodeToRenameDelay"
                                ]
                                + config["system"]["cpu"][coreCounter][
                                    "renameToIEWDelay"
                                ]
                                + config["system"]["cpu"][coreCounter][
                                    "iewToCommitDelay"
                                ]
                            )
                            cToDecode = config["system"]["cpu"][coreCounter][
                                "commitToDecodeDelay"
                            ]
                            cToFetch = config["system"]["cpu"][coreCounter][
                                "commitToFetchDelay"
                            ]
                            cToIew = config["system"]["cpu"][coreCounter][
                                "commitToIEWDelay"
                            ]
                            cToRename = config["system"]["cpu"][coreCounter][
                                "commitToRenameDelay"
                            ]
                            maxBase = max(
                                base, cToDecode, cToFetch, cToIew, cToRename
                            )
                            pipelineDepth = (
                                str(INT_EXE + base + maxBase)
                                + ","
                                + str(FP_EXE + base + maxBase)
                            )
                            logging.debug("Pipeline depth: %s" % pipelineDepth)
                            childValue = pipelineDepth
                        except KeyError:
                            logging.warning(
                                "No pipeline depth found in config"
                            )
                    if (
                        isinstance(childName, str)
                        and childName == "ALU_per_core"
                    ):
                        childValue = str(int(ALUPerCore))
                        logging.debug("ALU per core: %s" % childValue)
                    if (
                        isinstance(childName, str)
                        and childName == "MUL_per_core"
                    ):
                        childValue = str(int(MULPerCore))
                        logging.debug("MUL per core: %s" % childValue)
                    if (
                        isinstance(childName, str)
                        and childName == "FPU_per_core"
                    ):
                        childValue = str(int(FPUPerCore))
                        logging.debug("FPU per core: %s" % childValue)
                    if (
                        isinstance(childName, str)
                        and childName == "clock_rate"
                    ):
                        childValue = str(targetCoreClockrate)
                    if (isinstance(childName, str)) and (childName == "vdd"):
                        vdd = float(
                            config["system"]["cpu_voltage_domain"]["voltage"][
                                0
                            ]
                        )
                        logging.debug("Vdd: %f" % vdd)
                        childValue = str(vdd)
                    if (
                        isinstance(childName, str)
                    ) and childName == "fetch_width":
                        fetchWidth = config["system"]["cpu"][coreCounter][
                            "fetchWidth"
                        ]
                        logging.debug("Fetch width: %d" % fetchWidth)
                        childValue = str(fetchWidth)
                    if (
                        isinstance(childName, str)
                    ) and childName == "decode_width":
                        decodeWidth = config["system"]["cpu"][coreCounter][
                            "decodeWidth"
                        ]
                        logging.debug("Decode width: %d" % decodeWidth)
                        childValue = str(decodeWidth)

                    if (
                        isinstance(childName, str)
                    ) and childName == "issue_width":
                        issueWidth = config["system"]["cpu"][coreCounter][
                            "issueWidth"
                        ]
                        logging.debug("Issue width: %d" % issueWidth)
                        childValue = str(issueWidth)
                    if (
                        isinstance(childName, str)
                    ) and childName == "number_hardware_threads":
                        numThreads = config["system"]["cpu"][coreCounter][
                            "numThreads"
                        ]
                        logging.debug(
                            "Number of hardware threads: %d" % numThreads
                        )
                        childValue = str(numThreads)
                    if (
                        isinstance(childName, str)
                    ) and childName == "commit_width":
                        commitWidth = config["system"]["cpu"][coreCounter][
                            "commitWidth"
                        ]
                        logging.debug("Commit width: %d" % commitWidth)
                        childValue = str(commitWidth)
                    if (
                        isinstance(childName, str)
                    ) and childName == "ROB_size":
                        try:
                            robSize = config["system"]["cpu"][coreCounter][
                                "numROBEntries"
                            ]
                            logging.debug("ROB size: %d" % robSize)
                            childValue = str(robSize)
                        except KeyError:
                            logging.warning("No ROB size found in config")
                    if (
                        isinstance(childName, str)
                    ) and childName == "phy_Regs_IRF_size":
                        try:
                            phyRegsIRFSize = config["system"]["cpu"][
                                coreCounter
                            ]["numPhysIntRegs"]
                            logging.debug(
                                "Physical IRF size: %d" % phyRegsIRFSize
                            )
                            childValue = str(phyRegsIRFSize)
                        except KeyError:
                            logging.warning(
                                "No physical IRF size found in config"
                            )
                    if (
                        isinstance(childName, str)
                    ) and childName == "phy_Regs_FRF_size":
                        try:
                            phyRegsFRFSize = config["system"]["cpu"][
                                coreCounter
                            ]["numPhysFloatRegs"]
                            logging.debug(
                                "Physical FRF size: %d" % phyRegsFRFSize
                            )
                            childValue = str(phyRegsFRFSize)
                        except KeyError:
                            logging.warning(
                                "No physical FRF size found in config"
                            )
                    if (
                        isinstance(childName, str)
                    ) and childName == "store_buffer_size":
                        try:
                            storeBufferSize = config["system"]["cpu"][
                                coreCounter
                            ]["SQEntries"]
                            logging.debug(
                                "Store buffer size: %d" % storeBufferSize
                            )
                            childValue = str(storeBufferSize)
                        except KeyError:
                            logging.warning(
                                "No store buffer size found in config"
                            )
                    if (
                        isinstance(childName, str)
                    ) and childName == "load_buffer_size":
                        try:
                            loadBufferSize = config["system"]["cpu"][
                                coreCounter
                            ]["LQEntries"]
                            logging.debug(
                                "Load buffer size: %d" % loadBufferSize
                            )
                            childValue = str(loadBufferSize)
                        except KeyError:
                            logging.warning(
                                "No load buffer size found in config"
                            )
                    if (
                        isinstance(childName, str)
                    ) and childName == "RAS_size":
                        try:
                            rasSize = config["system"]["cpu"][coreCounter][
                                "branchPred"
                            ]["RASSize"]
                            logging.debug("RAS size: %d" % rasSize)
                            childValue = str(rasSize)
                        except KeyError:
                            logging.warning("No RAS size found in config")
                    if (
                        isinstance(childName, str)
                    ) and childName == "total_instructions":
                        try:
                            if numCores == 1:
                                totalInstructions = int(
                                    stats["system.cpu.commitStats0.numInsts"]
                                )
                            else:
                                try:
                                    path = (
                                        "system.cpu"
                                        + str(coreCounter)
                                        + ".commitStats0.numInsts"
                                    )
                                    totalInstructions = int(stats[path])
                                except KeyError:
                                    totalInstructions = 0
                        except KeyError:
                            totalInstructions = 0
                        logging.debug(
                            "Total instructions: %d" % totalInstructions
                        )
                        childValue = str(totalInstructions)
                    if (
                        isinstance(childName, str)
                    ) and childName == "int_instructions":
                        if numCores == 1:
                            intInstructions = int(
                                stats["system.cpu.commitStats0.numIntInsts"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commitStats0.numIntInsts"
                            )
                            intInstructions = int(stats[path])

                        logging.debug("Int instructions: %d" % intInstructions)
                        childValue = str(intInstructions)

                    if (
                        isinstance(childName, str)
                    ) and childName == "fp_instructions":
                        if numCores == 1:
                            fpInstructions = int(
                                stats["system.cpu.commitStats0.numFpInsts"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commitStats0.numFpInsts"
                            )
                            fpInstructions = int(stats[path])

                        logging.debug("FP instructions: %d" % fpInstructions)
                        childValue = str(fpInstructions)

                    if (isinstance(childName, str)) and (
                        childName == "branch_instructions"
                    ):
                        try:
                            if numCores == 1:
                                branchInstructions = int(
                                    stats[
                                        "system.cpu.branchPred.condPredicted"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".branchPred.condPredicted"
                                )
                                branchInstructions = int(stats[path])
                            logging.debug(
                                "Branch instructions: %d" % branchInstructions
                            )
                            childValue = str(branchInstructions)
                        except KeyError:
                            logging.warning(
                                "No branch instructions found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "branch_mispredictions"
                    ):
                        try:
                            if numCores == 1:
                                branchMispredictions = int(
                                    stats[
                                        "system.cpu.branchPred.condIncorrect"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".branchPred.condIncorrect"
                                )
                                branchMispredictions = int(stats[path])
                            logging.debug(
                                "Branch mispredictions: %d"
                                % branchMispredictions
                            )
                            childValue = str(branchMispredictions)
                        except KeyError:
                            logging.warning(
                                "No branch mispredictions found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "load_instructions"
                    ):
                        if numCores == 1:
                            loadInstructions = int(
                                stats["system.cpu.commitStats0.numLoadInsts"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commitStats0.numLoadInsts"
                            )
                            loadInstructions = int(stats[path])

                        logging.debug(
                            "Load instructions: %d" % loadInstructions
                        )
                        childValue = str(loadInstructions)
                    if (isinstance(childName, str)) and (
                        childName == "store_instructions"
                    ):
                        if numCores == 1:
                            storeInstructions = int(
                                stats["system.cpu.commitStats0.numStoreInsts"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commitStats0.numStoreInsts"
                            )
                            storeInstructions = int(stats[path])

                        logging.debug(
                            "Store instructions: %d" % storeInstructions
                        )
                        childValue = str(storeInstructions)
                    if (isinstance(childName, str)) and (
                        childName == "committed_instructions"
                    ):
                        if numCores == 1:
                            committedInstructions = int(
                                stats[
                                    "system.cpu.commit.numCommittedDist::total"
                                ]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commit.numCommittedDist::total"
                            )
                            committedInstructions = int(stats[path])
                        logging.debug(
                            "Committed instructions: %d"
                            % committedInstructions
                        )
                        childValue = str(committedInstructions)
                    if (isinstance(childName, str)) and (
                        childName == "total_cycles"
                    ):
                        if numCores == 1:
                            totalCycles = int(stats["system.cpu.numCycles"])
                        else:
                            path = (
                                "system.cpu" + str(coreCounter) + ".numCycles"
                            )
                            totalCycles = int(stats[path])

                        logging.debug("Total cycles: %d" % totalCycles)
                        childValue = str(totalCycles)
                    if (isinstance(childName, str)) and (
                        childName == "idle_cycles"
                    ):
                        try:
                            if numCores == 1:
                                idleCycles = int(
                                    stats["system.cpu.idleCycles"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".idleCycles"
                                )
                                idleCycles = int(stats[path])
                        except KeyError:
                            idleCycles = 0
                        logging.debug("Idle cycles: %d" % idleCycles)
                        childValue = str(idleCycles)

                    if (isinstance(childName, str)) and (
                        childName == "busy_cycles"
                    ):
                        busyCycles = totalCycles - idleCycles
                        logging.debug("Busy cycles: %d" % busyCycles)
                        childValue = str(busyCycles)
                    if (isinstance(childName, str)) and (
                        childName == "ROB_reads"
                    ):
                        if numCores == 1:
                            robReads = int(stats["system.cpu.rob.reads"])
                        else:
                            path = (
                                "system.cpu" + str(coreCounter) + ".rob.reads"
                            )
                            robReads = int(stats[path])
                        logging.debug("ROB reads: %d" % robReads)
                        childValue = str(robReads)

                    if (isinstance(childName, str)) and (
                        childName == "ROB_writes"
                    ):
                        if numCores == 1:
                            robWrites = int(stats["system.cpu.rob.writes"])
                        else:
                            path = (
                                "system.cpu" + str(coreCounter) + ".rob.writes"
                            )
                            robWrites = int(stats[path])
                        logging.debug("ROB writes: %d" % robWrites)
                        childValue = str(robWrites)
                    if (isinstance(childName, str)) and (
                        childName == "int_regfile_reads"
                    ):
                        try:
                            if numCores == 1:
                                intRegfileReads = int(
                                    stats[
                                        "system.cpu.executeStats0.numIntRegReads"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".executeStats0.numIntRegReads"
                                )
                                intRegfileReads = int(stats[path])
                        except KeyError:
                            intRegfileReads = 0

                        logging.debug(
                            "Int regfile reads: %d" % intRegfileReads
                        )
                        childValue = str(intRegfileReads)
                    if (isinstance(childName, str)) and (
                        childName == "float_regfile_reads"
                    ):
                        try:
                            if numCores == 1:
                                floatRegfileReads = int(
                                    stats[
                                        "system.cpu.executeStats0.numFpRegReads"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".executeStats0.numFpRegReads"
                                )
                                floatRegfileReads = int(stats[path])
                        except KeyError:
                            floatRegfileReads = 0
                        logging.debug(
                            "Float regfile reads: %d" % floatRegfileReads
                        )
                        childValue = str(floatRegfileReads)
                    if (isinstance(childName, str)) and (
                        childName == "int_regfile_writes"
                    ):
                        try:
                            if numCores == 1:
                                intRegfileWrites = int(
                                    stats[
                                        "system.cpu.executeStats0.numIntRegWrites"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".executeStats0.numIntRegWrites"
                                )
                                intRegfileWrites = int(stats[path])
                        except KeyError:
                            intRegfileWrites = 0
                        logging.debug(
                            "Int regfile writes: %d" % intRegfileWrites
                        )
                        childValue = str(intRegfileWrites)
                    if (isinstance(childName, str)) and (
                        childName == "float_regfile_writes"
                    ):
                        if numCores == 1:
                            floatRegfileWrites = int(
                                stats[
                                    "system.cpu.executeStats0.numFpRegWrites"
                                ]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".executeStats0.numFpRegWrites"
                            )
                            floatRegfileWrites = int(stats[path])
                        logging.debug(
                            "Float regfile writes: %d" % floatRegfileWrites
                        )
                        childValue = str(floatRegfileWrites)

                    if (isinstance(childName, str)) and (
                        childName == "function_calls"
                    ):
                        if numCores == 1:
                            functionCalls = int(
                                stats["system.cpu.commit.functionCalls"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".commit.functionCalls"
                            )
                            functionCalls = int(stats[path])
                        logging.debug("Function calls: %d" % functionCalls)
                        childValue = str(functionCalls)
                    if (isinstance(childName, str)) and (
                        childName == "ialu_accesses"
                    ):
                        if numCores == 1:
                            ialuAccesses = int(
                                stats["system.cpu.intAluAccesses"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".intAluAccesses"
                            )
                            ialuAccesses = int(stats[path])
                        logging.debug("Int ALU accesses: %d" % ialuAccesses)
                        childValue = str(ialuAccesses)
                    if (isinstance(childName, str)) and (
                        childName == "fpu_accesses"
                    ):
                        if numCores == 1:
                            fpuAccesses = int(
                                stats["system.cpu.fpAluAccesses"]
                            )
                        else:
                            path = (
                                "system.cpu"
                                + str(coreCounter)
                                + ".fpAluAccesses"
                            )
                            fpuAccesses = int(stats[path])
                        logging.debug("FPU accesses: %d" % fpuAccesses)
                        childValue = str(fpuAccesses)
                    if (isinstance(childName, str)) and (
                        childName == "rename_reads"
                    ):
                        try:
                            if numCores == 1:
                                renameReads = int(
                                    stats["system.cpu.rename.intLookups"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".rename.intLookups"
                                )
                                renameReads = int(stats[path])
                            logging.debug("Rename reads: %d" % renameReads)
                            childValue = str(renameReads)
                        except KeyError:
                            logging.warning("No rename reads found in stats")
                    if (isinstance(childName, str)) and (
                        childName == "rename_writes"
                    ):
                        try:
                            if numCores == 1:
                                renameWrites = int(
                                    float(
                                        stats[
                                            "system.cpu.rename.renamedOperands"
                                        ]
                                    )
                                    * float(
                                        stats["system.cpu.rename.intLookups"]
                                    )
                                    / float(stats["system.cpu.rename.lookups"])
                                )
                            else:
                                renameWrites = int(
                                    float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.renamedOperands"
                                        ]
                                    )
                                    * float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.intLookups"
                                        ]
                                    )
                                    / float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.lookups"
                                        ]
                                    )
                                )
                            logging.debug("Rename writes: %d" % renameWrites)
                            childValue = str(renameWrites)
                        except KeyError:
                            logging.warning("No rename writes found in stats")

                    if (isinstance(childName, str)) and (
                        childName == "fp_rename_reads"
                    ):
                        try:
                            if numCores == 1:
                                fpRenameReads = int(
                                    stats["system.cpu.rename.fpLookups"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".rename.fpLookups"
                                )
                                fpRenameReads = int(stats[path])
                            logging.debug(
                                "FP rename reads: %d" % fpRenameReads
                            )
                            childValue = str(fpRenameReads)
                        except KeyError:
                            logging.warning(
                                "No FP rename reads found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "fp_rename_writes"
                    ):
                        try:
                            if numCores == 1:
                                fpRenameWrites = int(
                                    float(
                                        stats[
                                            "system.cpu.rename.renamedOperands"
                                        ]
                                    )
                                    * float(
                                        stats["system.cpu.rename.fpLookups"]
                                    )
                                    / float(stats["system.cpu.rename.lookups"])
                                )
                            else:
                                fpRenameWrites = int(
                                    float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.renamedOperands"
                                        ]
                                    )
                                    * float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.fpLookups"
                                        ]
                                    )
                                    / float(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".rename.lookups"
                                        ]
                                    )
                                )

                            logging.debug(
                                "FP rename writes: %d" % fpRenameWrites
                            )
                            childValue = str(fpRenameWrites)
                        except KeyError:
                            logging.warning(
                                "No FP rename writes found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "instruction_buffer_size"
                    ):
                        try:
                            instructionBufferSize = int(
                                config["system"]["cpu"][coreCounter][
                                    "fetchBufferSize"
                                ]
                            )
                            logging.debug(
                                "Instruction buffer size: %d"
                                % instructionBufferSize
                            )
                            childValue = str(instructionBufferSize)
                        except KeyError:
                            logging.warning(
                                "No instruction buffer size found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "instruction_window_size"
                    ):
                        try:
                            instructionWindowSize = int(
                                int(
                                    config["system"]["cpu"][coreCounter][
                                        "numIQEntries"
                                    ]
                                )
                                / 2
                            )
                            logging.debug(
                                "Instruction window size: %d"
                                % instructionWindowSize
                            )
                            childValue = str(instructionWindowSize)
                        except KeyError:
                            logging.warning(
                                "No instruction window size found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "fp_instruction_window_size"
                    ):
                        try:
                            fpInstructionWindowSize = int(
                                int(
                                    config["system"]["cpu"][coreCounter][
                                        "numIQEntries"
                                    ]
                                )
                                / 2
                            )
                            logging.debug(
                                "FP instruction window size: %d"
                                % fpInstructionWindowSize
                            )
                            childValue = str(fpInstructionWindowSize)
                        except KeyError:
                            logging.warning(
                                "No FP instruction window size found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "inst_window_reads"
                    ):
                        try:
                            if numCores == 1:
                                instWindowReads = int(
                                    stats["system.cpu.intInstQueueReads"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".intInstQueueReads"
                                )
                                instWindowReads = int(stats[path])
                            logging.debug(
                                "Instruction window reads: %d"
                                % instWindowReads
                            )
                            childValue = str(instWindowReads)
                        except KeyError:
                            logging.warning(
                                "No instruction window reads found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "inst_window_writes"
                    ):
                        try:
                            if numCores == 1:
                                instWindowWrites = int(
                                    stats["system.cpu.intInstQueueWrites"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".intInstQueueWrites"
                                )
                                instWindowWrites = int(stats[path])
                            logging.debug(
                                "Instruction window writes: %d"
                                % instWindowWrites
                            )
                            childValue = str(instWindowWrites)
                        except KeyError:
                            logging.warning(
                                "No instruction window writes found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "inst_window_wakeup_accesses"
                    ):
                        try:
                            if numCores == 1:
                                intInstWindowReads = int(
                                    stats[
                                        "system.cpu.intInstQueueWakeupAccesses"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".intInstQueueWakeupAccesses"
                                )
                                intInstWindowReads = int(stats[path])
                            logging.debug(
                                "Int instruction window reads: %d"
                                % intInstWindowReads
                            )
                            childValue = str(intInstWindowReads)
                        except KeyError:
                            logging.warning(
                                "No FP instruction window reads found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "fp_inst_window_reads"
                    ):
                        try:
                            if numCores == 1:
                                fpInstWindowReads = int(
                                    stats["system.cpu.fpInstQueueReads"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".fpInstQueueReads"
                                )
                                fpInstWindowReads = int(stats[path])
                            logging.debug(
                                "FP instruction window reads: %d"
                                % fpInstWindowReads
                            )
                            childValue = str(fpInstWindowReads)
                        except KeyError:
                            logging.warning(
                                "No FP instruction window reads found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "fp_inst_window_writes"
                    ):
                        try:
                            if numCores == 1:
                                fpInstWindowWrites = int(
                                    stats["system.cpu.fpInstQueueWrites"]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".fpInstQueueWrites"
                                )
                                fpInstWindowWrites = int(stats[path])
                            logging.debug(
                                "FP instruction window writes: %d"
                                % fpInstWindowWrites
                            )
                            childValue = str(fpInstWindowWrites)
                        except KeyError:
                            logging.warning(
                                "No FP instruction window writes found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "fp_inst_window_wakeup_accesses"
                    ):
                        try:
                            if numCores == 1:
                                fpInstWindowWakeupAccesses = int(
                                    stats[
                                        "system.cpu.fpInstQueueWakeupAccesses"
                                    ]
                                )
                            else:
                                path = (
                                    "system.cpu"
                                    + str(coreCounter)
                                    + ".fpInstQueueWakeupAccesses"
                                )
                                fpInstWindowWakeupAccesses = int(stats[path])
                            logging.debug(
                                "FP instruction window wakeup accesses: %d"
                                % fpInstWindowWakeupAccesses
                            )
                            childValue = str(fpInstWindowWakeupAccesses)
                        except KeyError:
                            logging.warning(
                                "No FP instruction window wakeup accesses found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "mul_accesses"
                    ):
                        try:
                            if numCores == 1:
                                mulAccesses = int(
                                    int(
                                        stats[
                                            "system.cpu.statIssuedInstType_0::IntDiv"
                                        ]
                                    )
                                    + int(
                                        stats[
                                            "system.cpu.statIssuedInstType_0::IntMult"
                                        ]
                                    )
                                )
                            else:
                                mulAccesses = int(
                                    int(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".statIssuedInstType_0::IntDiv"
                                        ]
                                    )
                                    + int(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".statIssuedInstType_0::IntMult"
                                        ]
                                    )
                                )
                            logging.debug("Mul accesses: %d" % mulAccesses)
                            childValue = str(mulAccesses)
                        except KeyError:
                            logging.warning("No mul accesses found in stats")
                        except KeyError:
                            logging.warning("No mul accesses found in stats")
                    if (isinstance(childName, str)) and (
                        childName == "cdb_alu_accesses"
                    ):
                        try:
                            if numCores == 1:
                                cdbAluAccesses = int(
                                    stats["system.cpu.intAluAccesses"]
                                )
                            else:
                                cdbAluAccesses = int(
                                    stats[
                                        "system.cpu"
                                        + str(coreCounter)
                                        + ".intAluAccesses"
                                    ]
                                )
                            logging.debug(
                                "CDB ALU accesses: %d" % cdbAluAccesses
                            )
                            childValue = str(cdbAluAccesses)
                        except KeyError:
                            logging.warning(
                                "No CDB ALU accesses found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "cdb_mul_accesses"
                    ):
                        try:
                            if numCores == 1:
                                cdbMulAccesses = int(
                                    int(
                                        stats[
                                            "system.cpu.statIssuedInstType_0::IntDiv"
                                        ]
                                    )
                                    + int(
                                        stats[
                                            "system.cpu.statIssuedInstType_0::IntMult"
                                        ]
                                    )
                                )
                            else:
                                cdbMulAccesses = int(
                                    int(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".statIssuedInstType_0::IntDiv"
                                        ]
                                    )
                                    + int(
                                        stats[
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".statIssuedInstType_0::IntMult"
                                        ]
                                    )
                                )
                            logging.debug(
                                "cdb Mul accesses: %d" % cdbMulAccesses
                            )
                            childValue = str(cdbMulAccesses)
                        except KeyError:
                            logging.warning(
                                "No cdb Mul accesses found in stats"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "cdb_fpu_accesses"
                    ):
                        try:
                            if numCores == 1:
                                cdbFpuAccesses = int(
                                    stats["system.cpu.fpAluAccesses"]
                                )
                            else:
                                cdbFpuAccesses = int(
                                    stats[
                                        "system.cpu"
                                        + str(coreCounter)
                                        + ".fpAluAccesses"
                                    ]
                                )
                            logging.debug(
                                "CDB FPU accesses: %d" % cdbFpuAccesses
                            )
                            childValue = str(cdbFpuAccesses)
                        except KeyError:
                            logging.warning(
                                "No CDB FPU accesses found in stats"
                            )
                    # if (isinstance(childName, str)) and (
                    #     childName == "IFU_duty_cycle"
                    # ):
                    #     childValue = str(IFUDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "LSU_duty_cycle"
                    # ):
                    #     childValue = str(LSUDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "MemManU_I_duty_cycle"
                    # ):
                    #     childValue = str(MemManUIDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "MemManU_D_duty_cycle"
                    # ):
                    #     childValue = str(MemManUDDutyeCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "ALU_duty_cycle"
                    # ):
                    #     childValue = str(IntDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "MUL_duty_cycle"
                    # ):
                    #     childValue = str(MULDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "FPU_duty_cycle"
                    # ):
                    #     childValue = str(FPUDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "ALU_cdb_duty_cycle"
                    # ):
                    #     childValue = str(IntDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "MUL_cdb_duty_cycle"
                    # ):
                    #     childValue = str(MULDutyCycle)
                    # if (isinstance(childName, str)) and (
                    #     childName == "FPU_cdb_duty_cycle"
                    # ):
                    #     childValue = str(FPUDutyCycle)

                    # replace name
                    if isinstance(childId, str) and "core" in childId:
                        childId = childId.replace(
                            "core", "core" + str(coreCounter)
                        )
                    if (
                        isinstance(childValue, str)
                        and "cpu." in childValue
                        and "stats" in childValue.split(".")[0]
                    ):
                        childValue = childValue.replace(
                            "cpu.", "cpu" + str(coreCounter) + "."
                        )
                    if (
                        isinstance(childValue, str)
                        and "cpu." in childValue
                        and "config" in childValue.split(".")[0]
                    ):
                        childValue = childValue.replace(
                            "cpu.", "cpu." + str(coreCounter) + "."
                        )
                    if len(list(coreChild)) != 0:
                        for level2Child in coreChild:
                            level2ChildValue = level2Child.attrib.get("value")
                            level2ChildName = level2Child.attrib.get("name")
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "local_predictor_size"
                            ):
                                try:
                                    localPredictorSize = int(
                                        log2(
                                            config["system"]["cpu"][
                                                coreCounter
                                            ]["branchPred"][
                                                "localPredictorSize"
                                            ]
                                        )
                                    )
                                    ctrlBits = config["system"]["cpu"][
                                        coreCounter
                                    ]["branchPred"]["localCtrBits"]
                                    level2ChildValue = (
                                        str(localPredictorSize)
                                        + ","
                                        + str(ctrlBits)
                                    )
                                except KeyError:
                                    logging.warning(
                                        "No local predictor size found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "local_predictor_entries"
                            ):
                                try:
                                    localPredictorEntries = config["system"][
                                        "cpu"
                                    ][coreCounter]["branchPred"][
                                        "localHistoryTableSize"
                                    ]
                                    logging.debug(
                                        "Local predictor entries: %d"
                                        % localPredictorEntries
                                    )
                                    level2ChildValue = str(
                                        localPredictorEntries
                                    )
                                except KeyError:
                                    logging.warning(
                                        "No local predictor entries found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "global_predictor_size"
                            ):
                                try:
                                    globalPredictorSize = config["system"][
                                        "cpu"
                                    ][coreCounter]["branchPred"][
                                        "globalPredictorSize"
                                    ]
                                    logging.debug(
                                        "Global predictor size: %d"
                                        % globalPredictorSize
                                    )
                                    level2ChildValue = str(globalPredictorSize)
                                except KeyError:
                                    logging.warning(
                                        "No global predictor size found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "global_predictor_bits"
                            ):
                                try:
                                    globalPredictorBits = config["system"][
                                        "cpu"
                                    ][coreCounter]["branchPred"][
                                        "globalCtrBits"
                                    ]
                                    logging.debug(
                                        "Global predictor bits: %d"
                                        % globalPredictorBits
                                    )
                                    level2ChildValue = str(globalPredictorBits)
                                except KeyError:
                                    logging.warning(
                                        "No global predictor bits found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "chooser_predictor_entries"
                            ):
                                try:
                                    chooserPredictorSize = config["system"][
                                        "cpu"
                                    ][coreCounter]["branchPred"][
                                        "choicePredictorSize"
                                    ]
                                    logging.debug(
                                        "Chooser predictor size: %d"
                                        % chooserPredictorSize
                                    )
                                    level2ChildValue = str(
                                        chooserPredictorSize
                                    )
                                except KeyError:
                                    logging.warning(
                                        "No chooser predictor size found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "chooser_predictor_bits"
                            ):
                                try:
                                    chooserPredictorBits = config["system"][
                                        "cpu"
                                    ][coreCounter]["branchPred"][
                                        "choiceCtrBits"
                                    ]
                                    logging.debug(
                                        "Chooser predictor bits: %d"
                                        % chooserPredictorBits
                                    )
                                    level2ChildValue = str(
                                        chooserPredictorBits
                                    )
                                except KeyError:
                                    logging.warning(
                                        "No chooser predictor bits found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "number_entries"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "itlb"
                                ):
                                    try:
                                        numEntries = config["system"]["cpu"][
                                            coreCounter
                                        ]["mmu"]["itb"]["size"]
                                        logging.debug(
                                            "itlb Number of entries: %d"
                                            % numEntries
                                        )
                                        level2ChildValue = str(numEntries)
                                    except KeyError:
                                        logging.warning(
                                            "No itlb entries found in configs"
                                        )
                                if (isinstance(childName, str)) and (
                                    childName == "dtlb"
                                ):
                                    try:
                                        numEntries = config["system"]["cpu"][
                                            coreCounter
                                        ]["mmu"]["dtb"]["size"]
                                        logging.debug(
                                            "dtlb Number of entries: %d"
                                            % numEntries
                                        )
                                        level2ChildValue = str(numEntries)
                                    except KeyError:
                                        logging.warning(
                                            "No dtlb entries found in configs"
                                        )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "total_accesses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "itlb"
                                ):
                                    try:
                                        if numCores == 1:
                                            totalAccesses = int(
                                                stats[
                                                    "system.cpu.mmu.itb.accesses"
                                                ]
                                            )
                                            # totalAccesses = int(stats["system.cpu.mmu.itb.rdAccesses"]) + int(
                                            #     stats["system.cpu.mmu.itb.wrAccesses"]
                                            # )
                                        else:
                                            totalAccesses = int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.itb.rdAccesses"
                                                ]
                                            ) + int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.itb.wrAccesses"
                                                ]
                                            )

                                        logging.debug(
                                            "itlb Total accesses: %d"
                                            % totalAccesses
                                        )
                                        level2ChildValue = str(totalAccesses)
                                    except KeyError:
                                        logging.warning(
                                            "No itlb accesses found in stats"
                                        )
                                if (isinstance(childName, str)) and (
                                    childName == "dtlb"
                                ):
                                    try:
                                        if numCores == 1:
                                            totalAccesses = int(
                                                stats[
                                                    "system.cpu.mmu.dtb.accesses"
                                                ]
                                            )
                                            # totalAccesses = int(stats["system.cpu.mmu.dtb.rdAccesses"]) + int(
                                            #     stats["system.cpu.mmu.dtb.wrAccesses"]
                                            # )
                                        else:
                                            totalAccesses = int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.dtb.rdAccesses"
                                                ]
                                            ) + int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.dtb.wrAccesses"
                                                ]
                                            )

                                        logging.debug(
                                            "dtlb Total accesses: %d"
                                            % totalAccesses
                                        )
                                        level2ChildValue = str(totalAccesses)
                                    except KeyError:
                                        logging.warning(
                                            "No dtlb accesses found in stats"
                                        )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "total_misses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "itlb"
                                ):
                                    try:
                                        if numCores == 1:
                                            totalMisses = int(
                                                stats[
                                                    "system.cpu.mmu.itb.misses"
                                                ]
                                            )
                                        else:
                                            totalMisses = int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.itb.rdMisses"
                                                ]
                                            ) + int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.itb.wrMisses"
                                                ]
                                            )

                                        logging.debug(
                                            "itlb Total misses: %d"
                                            % totalMisses
                                        )
                                        level2ChildValue = str(totalMisses)
                                    except KeyError:
                                        logging.warning(
                                            "No itlb misses found in stats"
                                        )
                                if (isinstance(childName, str)) and (
                                    childName == "dtlb"
                                ):
                                    try:
                                        if numCores == 1:
                                            totalMisses = int(
                                                stats[
                                                    "system.cpu.mmu.dtb.misses"
                                                ]
                                            )
                                        else:
                                            totalMisses = int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.dtb.rdMisses"
                                                ]
                                            ) + int(
                                                stats[
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    + ".mmu.dtb.wrMisses"
                                                ]
                                            )

                                        logging.debug(
                                            "dtlb Total misses: %d"
                                            % totalMisses
                                        )
                                        level2ChildValue = str(totalMisses)
                                    except KeyError:
                                        logging.warning(
                                            "No dtlb misses found in stats"
                                        )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "icache_config"
                            ):
                                icacheCapacity = config["system"]["cpu"][
                                    coreCounter
                                ]["icache"]["size"]
                                icacheBlockSize = config["system"]["cpu"][
                                    coreCounter
                                ]["icache"]["tags"]["block_size"]
                                icacheAssoc = config["system"]["cpu"][
                                    coreCounter
                                ]["icache"]["assoc"]
                                try:
                                    icacheBank = config["system"]["cpu"][
                                        coreCounter
                                    ]["icache"]["bank"]
                                except KeyError:
                                    icacheBank = 1
                                try:
                                    icacheThroughput = config["system"]["cpu"][
                                        coreCounter
                                    ]["icache"]["throughput"]
                                except KeyError:
                                    try:
                                        icacheThroughput = int(
                                            float(
                                                stats[
                                                    (
                                                        "system.cpu"
                                                        + str(coreCounter)
                                                        if numCores > 1
                                                        else "system.cpu"
                                                    )
                                                    + ".icache.overallAccesses::total"
                                                ]
                                            )
                                            * icacheBlockSize
                                            / float(
                                                stats[
                                                    (
                                                        "system.cpu"
                                                        + str(coreCounter)
                                                        if numCores > 1
                                                        else "system.cpu"
                                                    )
                                                    + ".numCycles"
                                                ]
                                            )
                                        )
                                    except KeyError:
                                        icacheThroughput = 0
                                icacheLatency = config["system"]["cpu"][
                                    coreCounter
                                ]["icache"]["response_latency"]
                                icacheOutputWidth = config["system"]["cpu"][
                                    coreCounter
                                ]["icache"]["tags"]["block_size"]
                                try:
                                    icachePolicy = config["system"]["cpu"][
                                        coreCounter
                                    ]["icache"]["cache_policy"]
                                except KeyError:
                                    icachePolicy = 1

                                level2ChildValue = (
                                    str(icacheCapacity)
                                    + ","
                                    + str(icacheBlockSize)
                                    + ","
                                    + str(icacheAssoc)
                                    + ","
                                    + str(icacheBank)
                                    + ","
                                    + str(icacheThroughput)
                                    + ","
                                    + str(icacheLatency)
                                    + ","
                                    + str(icacheOutputWidth)
                                    + ","
                                    + str(icachePolicy)
                                )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "dcache_config"
                            ):
                                dcacheCapacity = config["system"]["cpu"][
                                    coreCounter
                                ]["dcache"]["size"]
                                dcacheBlockSize = config["system"]["cpu"][
                                    coreCounter
                                ]["dcache"]["tags"]["block_size"]
                                dcacheAssoc = config["system"]["cpu"][
                                    coreCounter
                                ]["dcache"]["assoc"]
                                try:
                                    dcacheBank = config["system"]["cpu"][
                                        coreCounter
                                    ]["dcache"]["bank"]
                                except KeyError:
                                    dcacheBank = 1
                                try:
                                    dcacheThroughput = config["system"]["cpu"][
                                        coreCounter
                                    ]["dcache"]["throughput"]
                                except KeyError:
                                    try:
                                        dcacheThroughput = int(
                                            float(
                                                stats[
                                                    (
                                                        "system.cpu"
                                                        + str(coreCounter)
                                                        if numCores > 1
                                                        else "system.cpu"
                                                    )
                                                    + ".dcache.overallAccesses::total"
                                                ]
                                            )
                                            * dcacheBlockSize
                                            / float(
                                                stats[
                                                    (
                                                        "system.cpu"
                                                        + str(coreCounter)
                                                        if numCores > 1
                                                        else "system.cpu"
                                                    )
                                                    + ".numCycles"
                                                ]
                                            )
                                        )
                                    except KeyError:
                                        dcacheThroughput = 0
                                dcacheLatency = config["system"]["cpu"][
                                    coreCounter
                                ]["dcache"]["response_latency"]
                                dcacheOutputWidth = config["system"]["cpu"][
                                    coreCounter
                                ]["dcache"]["tags"]["block_size"]
                                try:
                                    dcachePolicy = config["system"]["cpu"][
                                        coreCounter
                                    ]["dcache"]["cache_policy"]
                                except KeyError:
                                    dcachePolicy = 1

                                level2ChildValue = (
                                    str(dcacheCapacity)
                                    + ","
                                    + str(dcacheBlockSize)
                                    + ","
                                    + str(dcacheAssoc)
                                    + ","
                                    + str(dcacheBank)
                                    + ","
                                    + str(dcacheThroughput)
                                    + ","
                                    + str(dcacheLatency)
                                    + ","
                                    + str(dcacheOutputWidth)
                                    + ","
                                    + str(dcachePolicy)
                                )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "read_accesses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "icache"
                                ):
                                    try:
                                        if numCores == 1:
                                            readAccesses = int(
                                                stats[
                                                    "system.cpu.icache.ReadReq.accesses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".icache.ReadReq.accesses::total"
                                            )
                                            readAccesses = int(stats[path])
                                    except KeyError:
                                        readAccesses = 0
                                    logging.debug(
                                        "icache Read accesses: %d"
                                        % readAccesses
                                    )
                                    level2ChildValue = str(readAccesses)
                                if (isinstance(childName, str)) and (
                                    childName == "dcache"
                                ):
                                    try:
                                        if numCores == 1:
                                            readAccesses = int(
                                                stats[
                                                    "system.cpu.dcache.ReadReq.accesses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".dcache.ReadReq.accesses::total"
                                            )
                                            readAccesses = int(stats[path])
                                    except KeyError:
                                        readAccesses = 0
                                    logging.debug(
                                        "dcache Read accesses: %d"
                                        % readAccesses
                                    )
                                    level2ChildValue = str(readAccesses)

                                if (isinstance(childName, str)) and (
                                    childName == "BTB"
                                ):
                                    try:
                                        if numCores == 1:
                                            readAccesses = int(
                                                stats[
                                                    "system.cpu.branchPred.BTBLookups"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".branchPred.BTBLookups"
                                            )
                                            readAccesses = int(stats[path])
                                    except KeyError:
                                        logging.warning(
                                            "No BTB reads found in stats"
                                        )
                                        readAccesses = 0

                                    logging.debug(
                                        "BTB Read accesses: %d" % readAccesses
                                    )
                                    level2ChildValue = str(readAccesses)

                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "write_accesses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "icache"
                                ):
                                    if numCores == 1:
                                        writeAccesses = int(
                                            stats[
                                                "system.cpu.icache.WriteReq.accesses::total"
                                            ]
                                        )
                                    else:
                                        path = (
                                            "system.cpu"
                                            + str(coreCounter)
                                            + ".icache.WriteReq.accesses::total"
                                        )
                                        writeAccesses = int(stats[path])
                                    logging.debug(
                                        "icache Write accesses: %d"
                                        % writeAccesses
                                    )
                                    level2ChildValue = str(writeAccesses)
                                if (isinstance(childName, str)) and (
                                    childName == "dcache"
                                ):
                                    try:
                                        if numCores == 1:
                                            writeAccesses = int(
                                                stats[
                                                    "system.cpu.dcache.WriteReq.accesses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".dcache.WriteReq.accesses::total"
                                            )
                                            writeAccesses = int(stats[path])
                                    except KeyError:
                                        writeAccesses = 0
                                    logging.debug(
                                        "dcache Write accesses: %d"
                                        % writeAccesses
                                    )
                                    level2ChildValue = str(writeAccesses)
                                if (isinstance(childName, str)) and (
                                    childName == "BTB"
                                ):
                                    try:
                                        if numCores == 1:
                                            writeAccesses = int(
                                                stats[
                                                    "system.cpu.branchPred.BTBHits"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".branchPred.BTBHits"
                                            )
                                            writeAccesses = int(stats[path])
                                    except KeyError:
                                        writeAccesses = 0
                                        logging.warning(
                                            "No BTB writes found in stats"
                                        )
                                    logging.debug(
                                        "BTB Write accesses: %d"
                                        % writeAccesses
                                    )
                                    level2ChildValue = str(writeAccesses)

                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "read_misses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "icache"
                                ):
                                    try:
                                        if numCores == 1:
                                            readMisses = int(
                                                stats[
                                                    "system.cpu.icache.ReadReq.misses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".icache.ReadReq.misses::total"
                                            )
                                            readMisses = int(stats[path])
                                    except KeyError:
                                        readMisses = 0
                                    logging.debug(
                                        "icache Read misses: %d" % readMisses
                                    )
                                    level2ChildValue = str(readMisses)
                                if (isinstance(childName, str)) and (
                                    childName == "dcache"
                                ):
                                    try:
                                        if numCores == 1:
                                            readMisses = int(
                                                stats[
                                                    "system.cpu.dcache.ReadReq.misses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".dcache.ReadReq.misses::total"
                                            )
                                            readMisses = int(stats[path])
                                    except KeyError:
                                        readMisses = 0

                                    logging.debug(
                                        "dcache Read misses: %d" % readMisses
                                    )
                                    level2ChildValue = str(readMisses)
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "write_misses"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "icache"
                                ):
                                    try:
                                        if numCores == 1:
                                            writeMisses = int(
                                                stats[
                                                    "system.cpu.icache.WriteReq.misses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".icache.WriteReq.misses::total"
                                            )
                                            writeMisses = int(stats[path])
                                    except KeyError:
                                        writeMisses = 0
                                        logging.warning(
                                            "No icache write misses found in stats"
                                        )

                                    logging.debug(
                                        "icache Write misses: %d" % writeMisses
                                    )
                                    level2ChildValue = str(writeMisses)
                                if (isinstance(childName, str)) and (
                                    childName == "dcache"
                                ):
                                    try:
                                        if numCores == 1:
                                            writeMisses = int(
                                                stats[
                                                    "system.cpu.dcache.WriteReq.misses::total"
                                                ]
                                            )
                                        else:
                                            path = (
                                                "system.cpu"
                                                + str(coreCounter)
                                                + ".dcache.WriteReq.misses::total"
                                            )
                                            writeMisses = int(stats[path])
                                    except KeyError:
                                        writeMisses = 0
                                        logging.warning(
                                            "No dcache write misses found in stats"
                                        )
                                    logging.debug(
                                        "dcache Write misses: %d" % writeMisses
                                    )
                                    level2ChildValue = str(writeMisses)
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "BTB_config"
                            ):
                                try:
                                    BTBConfig1 = config["system"]["cpu"][
                                        coreCounter
                                    ]["branchPred"]["BTBEntries"]
                                    BTBConfig2 = config["system"]["cpu"][
                                        coreCounter
                                    ]["branchPred"]["BTBTagSize"]
                                    BTBConfig3 = config["system"]["cpu"][
                                        coreCounter
                                    ]["branchPred"]["indirectBranchPred"][
                                        "indirectWays"
                                    ]
                                    try:
                                        BTBConfig4 = config["system"]["cpu"][
                                            coreCounter
                                        ]["branchPred"]["bank"]
                                    except KeyError:
                                        BTBConfig4 = 1
                                    try:
                                        cycles = float(
                                            stats[
                                                (
                                                    "system.cpu"
                                                    + str(coreCounter)
                                                    if numCores > 1
                                                    else "system.cpu"
                                                )
                                                + ".numCycles"
                                            ]
                                        )
                                        if cycles == 0:
                                            BTBConfig5 = 0
                                        else:
                                            BTBConfig5 = int(
                                                float(
                                                    stats[
                                                        (
                                                            "system.cpu"
                                                            + str(coreCounter)
                                                            if numCores > 1
                                                            else "system.cpu"
                                                        )
                                                        + ".branchPred.lookups"
                                                    ]
                                                )
                                                * BTBConfig2
                                                / cycles
                                            )
                                    except KeyError:
                                        # print keyError
                                        logging.warning(
                                            "KeyError occurred", exc_info=True
                                        )
                                        BTBConfig5 = 0
                                    BTBConfig6 = config["system"]["cpu"][
                                        coreCounter
                                    ]["icache"]["response_latency"]
                                    level2ChildValue = (
                                        str(BTBConfig1)
                                        + ","
                                        + str(BTBConfig2)
                                        + ","
                                        + str(BTBConfig3)
                                        + ","
                                        + str(BTBConfig4)
                                        + ","
                                        + str(BTBConfig5)
                                        + ","
                                        + str(BTBConfig6)
                                    )
                                except KeyError:
                                    logging.warning(
                                        "No BTB config found in config"
                                    )
                            if (isinstance(level2ChildName, str)) and (
                                level2ChildName == "buffer_sizes"
                            ):
                                if (isinstance(childName, str)) and (
                                    childName == "icache"
                                ):
                                    try:
                                        icacheBufferSize = config["system"][
                                            "cpu"
                                        ][coreCounter]["icache"]["mshrs"]
                                        logging.debug(
                                            "icache Buffer size: %d"
                                            % icacheBufferSize
                                        )
                                        level2ChildValue = (
                                            str(icacheBufferSize)
                                            + ","
                                            + str(icacheBufferSize)
                                            + ","
                                            + str(icacheBufferSize)
                                            + ","
                                            + str(icacheBufferSize)
                                        )
                                    except KeyError:
                                        logging.warning(
                                            "No icache buffer size found in config"
                                        )
                                if (isinstance(childName, str)) and (
                                    childName == "dcache"
                                ):
                                    try:
                                        dcacheBufferSize = config["system"][
                                            "cpu"
                                        ][coreCounter]["dcache"]["mshrs"]
                                        logging.debug(
                                            "dcache Buffer size: %d"
                                            % dcacheBufferSize
                                        )
                                        level2ChildValue = (
                                            str(dcacheBufferSize)
                                            + ","
                                            + str(dcacheBufferSize)
                                            + ","
                                            + str(dcacheBufferSize)
                                            + ","
                                            + str(dcacheBufferSize)
                                        )
                                    except KeyError:
                                        logging.warning(
                                            "No dcache buffer size found in config"
                                        )
                            if (
                                isinstance(level2ChildValue, str)
                                and "cpu." in level2ChildValue
                                and "stats" in level2ChildValue.split(".")[0]
                            ):
                                level2ChildValue = level2ChildValue.replace(
                                    "cpu.", "cpu" + str(coreCounter) + "."
                                )
                            if (
                                isinstance(level2ChildValue, str)
                                and "cpu." in level2ChildValue
                                and "config" in level2ChildValue.split(".")[0]
                            ):
                                level2ChildValue = level2ChildValue.replace(
                                    "cpu.", "cpu." + str(coreCounter) + "."
                                )
                            level2Child.attrib["value"] = level2ChildValue
                    if isinstance(childId, str):
                        coreChild.attrib["id"] = childId
                    if isinstance(childValue, str):
                        coreChild.attrib["value"] = childValue
                root[0][0].insert(elemCounter, coreElem)
                coreElem = copy.deepcopy(coreElemCopy)
                elemCounter += 1
            root[0][0].remove(child)
            elemCounter -= 1

        if child.attrib.get("name") == "L20":
            if numL2 == 0:
                children_to_remove.append(child)

            elif privateL2:
                l2Elem = copy.deepcopy(child)
                l2ElemCopy = copy.deepcopy(l2Elem)
                for l2Counter in range(numL2):
                    l2Elem.attrib["name"] = "L2" + str(l2Counter)
                    l2Elem.attrib["id"] = "system.L2" + str(l2Counter)
                    for l2Child in l2Elem:
                        childValue = l2Child.attrib.get("value")
                        if (
                            isinstance(childValue, str)
                            and "cpu." in childValue
                            and "stats" in childValue.split(".")[0]
                        ):
                            childValue = childValue.replace(
                                "cpu.", "cpu" + str(l2Counter) + "."
                            )
                        if (
                            isinstance(childValue, str)
                            and "cpu." in childValue
                            and "config" in childValue.split(".")[0]
                        ):
                            childValue = childValue.replace(
                                "cpu.", "cpu." + str(l2Counter) + "."
                            )
                        if isinstance(childValue, str):
                            l2Child.attrib["value"] = childValue
                    root[0][0].insert(elemCounter, l2Elem)
                    l2Elem = copy.deepcopy(l2ElemCopy)
                    elemCounter += 1
                root[0][0].remove(child)
            else:
                child.attrib["name"] = "L20"
                child.attrib["id"] = "system.L20"
                for l2Child in child:
                    childValue = l2Child.attrib.get("value")
                    childName = l2Child.attrib.get("name")
                    if (isinstance(childName, str)) and (
                        childName == "L2_config"
                    ):
                        capacity = config["system"]["l2"]["size"]
                        blockWidth = config["system"]["l2"]["tags"][
                            "block_size"
                        ]
                        associativity = config["system"]["l2"]["assoc"]
                        try:
                            bank = config["system"]["l2"]["bank"]
                        except KeyError:
                            bank = 1
                        try:
                            throughput = config["system"]["l2"]["throughput"]
                        except KeyError:
                            if numCores == 1:
                                try:
                                    throughput = int(
                                        float(
                                            stats[
                                                "system.l2.overallAccesses::total"
                                            ]
                                        )
                                        * blockWidth
                                        / float(stats["system.cpu.numCycles"])
                                    )
                                except KeyError:
                                    throughput = 0
                            else:
                                throughput = 0
                                for i in range(numCores):
                                    try:
                                        throughput += float(
                                            (
                                                float(
                                                    stats[
                                                        "system.l2.overallAccesses::cpu"
                                                        + str(i)
                                                        + ".inst"
                                                    ]
                                                )
                                                + float(
                                                    stats[
                                                        "system.l2.overallAccesses::cpu"
                                                        + str(i)
                                                        + ".data"
                                                    ]
                                                )
                                            )
                                            * blockWidth
                                            / float(
                                                stats[
                                                    "system.cpu"
                                                    + str(i)
                                                    + ".numCycles"
                                                ]
                                            )
                                        )
                                    except KeyError:
                                        throughput += 0
                                throughput = int(throughput)
                                logging.debug("L2 throughput: %d" % throughput)
                        latency = config["system"]["l2"]["response_latency"]
                        outputWidth = config["system"]["l2"]["tags"][
                            "block_size"
                        ]
                        try:
                            cachePolicy = config["system"]["l2"][
                                "cache_policy"
                            ]
                        except KeyError:
                            cachePolicy = 1
                        childValue = (
                            str(capacity)
                            + ","
                            + str(blockWidth)
                            + ","
                            + str(associativity)
                            + ","
                            + str(bank)
                            + ","
                            + str(throughput)
                            + ","
                            + str(latency)
                            + ","
                            + str(outputWidth)
                            + ","
                            + str(cachePolicy)
                        )
                    if (isinstance(childName, str)) and (
                        childName == "buffer_sizes"
                    ):
                        try:
                            l2bufferSize = config["system"]["l2"]["mshrs"]
                            logging.debug("L2 buffer size: %d" % l2bufferSize)
                            childValue = (
                                str(l2bufferSize)
                                + ","
                                + str(l2bufferSize)
                                + ","
                                + str(l2bufferSize)
                                + ","
                                + str(l2bufferSize)
                            )
                        except KeyError:
                            logging.warning(
                                "No L2 buffer size found in config"
                            )
                    if (isinstance(childName, str)) and (
                        childName == "clockrate"
                    ):
                        clkDomain = config["system"]["mem_ctrls"][0]["dram"][
                            "clk_domain"
                        ]
                        if clkDomain == "system.clk_domain":
                            targetMcClockrate = int(
                                10**6 / int(stats["system.clk_domain.clock"])
                            )
                        childValue = str(targetMcClockrate)
                    if (isinstance(childName, str)) and (childName == "vdd"):
                        try:
                            vdd = config["system"]["voltage_domain"][
                                "voltage"
                            ][0]
                            childValue = str(vdd)
                        except KeyError:
                            logging.warning("No Vdd found in config")
                    if (isinstance(childName, str)) and (
                        childName == "read_accesses"
                    ):
                        readAccesses = 0
                        try:
                            readAccesses += int(
                                stats[
                                    "system.l2.ReadSharedReq.accesses::total"
                                ]
                            )
                        except KeyError:
                            readAccesses += 0
                        try:
                            readAccesses += int(
                                stats["system.l2.ReadExReq.accesses::total"]
                            )
                        except KeyError:
                            readAccesses += 0
                        try:
                            readAccesses += int(
                                stats["system.l2.ReadCleanReq.accesses::total"]
                            )
                        except KeyError:
                            readAccesses += 0
                        childValue = str(readAccesses)
                    if (isinstance(childName, str)) and (
                        childName == "write_accesses"
                    ):
                        writeAccesses = 0
                        try:
                            writeAccesses += int(
                                stats["system.l2.UpgradeReq.accesses::total"]
                            )
                        except KeyError:
                            writeAccesses += 0
                        try:
                            writeAccesses += int(
                                stats[
                                    "system.l2.WritebackDirty.accesses::total"
                                ]
                            )
                        except KeyError:
                            writeAccesses += 0
                        childValue = str(writeAccesses)
                    if (isinstance(childName, str)) and (
                        childName == "read_misses"
                    ):
                        readMisses = 0
                        try:
                            readMisses += int(
                                stats["system.l2.ReadSharedReq.misses::total"]
                            )
                        except KeyError:
                            readMisses += 0
                        try:
                            readMisses += int(
                                stats["system.l2.ReadExReq.misses::total"]
                            )
                        except KeyError:
                            readMisses += 0
                        try:
                            readMisses += int(
                                stats["system.l2.ReadCleanReq.misses::total"]
                            )
                        except KeyError:
                            readMisses += 0
                        childValue = str(readMisses)
                    if (isinstance(childName, str)) and (
                        childName == "write_misses"
                    ):
                        writeMisses = 0
                        try:
                            writeMisses += int(
                                stats["system.l2.UpgradeReq.misses::total"]
                            )
                        except KeyError:
                            writeMisses += 0
                        try:
                            writeMisses += int(
                                stats["system.l2.WritebackDirty.misses::total"]
                            )
                        except KeyError:
                            writeMisses += 0
                        childValue = str(writeMisses)
                    if (isinstance(childName, str)) and (
                        childName == "duty_cycle"
                    ):
                        activeCycles = stats["system.l2.tags.tagAccesses"]
                        totalCycles = stats["simTicks"]
                        dutyCycle = float(activeCycles) / float(totalCycles)
                        childValue = str(dutyCycle)

                    l2Child.attrib["value"] = childValue

        if child.attrib.get("name") == "L30":
            # TODO: complete here.
            if numL3 == 0:
                children_to_remove.append(child)

        if child.attrib.get("name") == "mc":
            for mcChild in child:
                mcChildValue = mcChild.attrib.get("value")
                mcChildName = mcChild.attrib.get("name")
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "memory_accesses"
                ):
                    readAccesses = int(stats["system.mem_ctrls.readReqs"])
                    writeAccesses = int(stats["system.mem_ctrls.writeReqs"])
                    memoryAccesses = readAccesses + writeAccesses
                    logging.debug("Memory accesses: %d" % memoryAccesses)
                    mcChildValue = str(memoryAccesses)
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "memory_reads"
                ):
                    memoryReads = int(stats["system.mem_ctrls.readReqs"])
                    logging.debug("Memory reads: %d" % memoryReads)
                    mcChildValue = str(memoryReads)
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "memory_writes"
                ):
                    memoryWrites = int(stats["system.mem_ctrls.writeReqs"])
                    logging.debug("Memory writes: %d" % memoryWrites)
                    mcChildValue = str(memoryWrites)
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "mc_clock"
                ):
                    clkDomain = config["system"]["mem_ctrls"][0]["dram"][
                        "clk_domain"
                    ]
                    if clkDomain == "system.clk_domain":
                        targetMcClockrate = int(
                            10**6 / int(stats["system.clk_domain.clock"])
                        )
                    mcChildValue = str(targetMcClockrate)
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "block_size"
                ):
                    try:
                        blockSize = config["system"]["mem_ctrls"][0]["dram"][
                            "write_buffer_size"
                        ]
                        logging.debug("Block size: %d" % blockSize)
                        mcChildValue = str(blockSize)
                    except KeyError:
                        logging.warning("No block size found in config")
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "number_mcs"
                ):
                    try:
                        numMCs = len(config["system"]["mem_ctrls"])
                        logging.debug("Number of MCs: %d" % numMCs)
                        mcChildValue = str(numMCs)
                    except KeyError:
                        logging.warning("No number of MCs found in config")
                if (isinstance(mcChildName, str)) and (
                    mcChildName == "number_ranks"
                ):
                    try:
                        numRanks = config["system"]["mem_ctrls"][0]["dram"][
                            "ranks_per_channel"
                        ]
                        logging.debug("Number of ranks: %d" % numRanks)
                        mcChildValue = str(numRanks)
                    except KeyError:
                        logging.warning("No number of ranks found in config")

                mcChild.attrib["value"] = mcChildValue

    logging.debug("Removing %d number of children" % len(children_to_remove))
    for child in children_to_remove:
        root[0][0].remove(child)

    prettify(root)
    # templateMcpat.write(outputFile)


# for stats.txt?
def getConfValue(confStr):
    spltConf = re.split(r"\.", confStr)
    currConf = config
    currHierarchy = ""
    for x in spltConf:
        currHierarchy += x
        if x.isdigit():
            currConf = currConf[int(x)]
        elif x in currConf:
            # if isinstance(currConf, types.ListType):
            #     #this is mostly for system.cpu* as system.cpu is an array
            #     #This could be made better
            #     if x not in currConf[0]:
            #         print "%s does not exist in config" % currHierarchy
            #     else:
            #         currConf = currConf[0][x]
            # else:
            #         print "***WARNING: %s does not exist in config.***" % currHierarchy
            #         print "\t Please use the right config param in your McPAT template file"
            # else:
            currConf = currConf[x]
        currHierarchy += "."

    logging.info(confStr, currConf)

    return currConf


def dumpMcpatOut(outFile):
    """
    outfile: file reference to "mcpat-in.xml"
    """

    rootElem = templateMcpat.getroot()
    configMatch = re.compile(r"config\.([][a-zA-Z0-9_:\.]+)")

    # replace params with values from the GEM5 config file
    for param in rootElem.iter("param"):
        name = param.attrib["name"]
        value = param.attrib["value"]

        # if there is a config in this attrib
        if "config" in value:
            allConfs = configMatch.findall(value)

            for conf in allConfs:

                confValue = getConfValue(conf)
                value = re.sub("config." + conf, str(confValue), value)

            if "," in value:
                exprs = re.split(",", value)
                for i in range(len(exprs)):
                    try:
                        exprs[i] = str(eval(exprs[i]))
                    except Exception as e:
                        logging.error(
                            "Possibly "
                            + conf
                            + " does not exist in config"
                            + "\n\t set correct key string in template value"
                        )
                        raise

                param.attrib["value"] = ",".join(exprs)
            else:
                param.attrib["value"] = str(eval(str(value)))

    # replace stats with values from the GEM5 stats file
    statRe = re.compile(r"stats\.([a-zA-Z0-9_:\.]+)")
    for stat in rootElem.iter("stat"):
        name = stat.attrib["name"]
        value = stat.attrib["value"]
        if "stats" in value:
            allStats = statRe.findall(value)
            expr = value
            for i in range(len(allStats)):
                # print(allStats[i])
                if allStats[i] in stats:

                    expr = re.sub(
                        "stats.%s" % allStats[i], stats[allStats[i]], expr
                    )
                elif ".cpu0." in allStats[i]:
                    try:
                        cpu_stat = allStats[i].replace(".cpu0.", ".cpu.")
                        expr = re.sub(
                            "stats.%s" % allStats[i], stats[cpu_stat], expr
                        )
                    except KeyError:
                        logging.warning(
                            allStats[i]
                            + " does not exist in stats"
                            + "\n\t Maybe invalid stat in McPAT template file"
                        )
                else:
                    # expr = re.sub('stats.%s' % allStats[i], str(1), expr)
                    logging.warning(
                        allStats[i]
                        + " does not exist in stats"
                        + "\n\t Maybe invalid stat in McPAT template file"
                    )

            if "config" not in expr and "stats" not in expr:
                stat.attrib["value"] = str(eval(expr))

    # Write out the xml file
    templateMcpat.write(outFile.name)


def main():
    global args
    parser = create_parser()
    args = parser.parse_args()
    readStatsFile(args.stats)
    readConfigFile(args.config)
    readMcpatFile(args.template)

    prepareTemplate(args.output)

    dumpMcpatOut(args.output)


if __name__ == "__main__":
    main()
