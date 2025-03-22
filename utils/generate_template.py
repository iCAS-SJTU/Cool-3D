import os
import argparse
import yaml

xml_template_root = """<component id="root" name="root">"""
xml_template_system = """
	<component id="system" name="system">
		<!--McPAT will skip the components if number is set to 0 -->
		<param name="number_of_cores" value="4"/>
		<param name="number_of_L1Directories" value="0"/>
		<param name="number_of_L2Directories" value="0"/>
		<param name="number_of_L2s" value="0"/> <!-- This number means how many L2 clusters in each cluster there can be multiple banks/ports -->
		<param name="Private_L2" value ="1"/>
		<param name="number_of_L3s" value="0"/> <!-- This number means how many L3 clusters -->
		<param name="number_of_NoCs" value="1"/>
		<param name="homogeneous_cores" value="0"/><!--1 means homo -->
		<param name="homogeneous_L2s" value="0"/>
		<param name="homogeneous_L1Directories" value="0"/>
		<param name="homogeneous_L2Directories" value="0"/>
		<param name="homogeneous_L3s" value="0"/>
		<param name="homogeneous_ccs" value="1"/><!--cache coherece hardware -->
		<param name="homogeneous_NoCs" value="1"/>
		<param name="core_tech_node" value="45"/><!-- nm -->
		<param name="target_core_clockrate" value='%i'/><!--MHz -->
		<param name="temperature" value="330"/> <!-- Kelvin -->
		<param name="number_cache_levels" value="3"/>
		<param name="interconnect_projection_type" value="0"/><!--0: agressive wire technology; 1: conservative wire technology -->
		<param name="device_type" value="0"/><!--0: HP(High Performance Type); 1: LSTP(Low standby power) 2: LOP (Low Operating Power)  -->
		<param name="longer_channel_device" value="1"/><!-- 0 no use; 1 use when approperiate -->
		<param name="power_gating" value="1"/><!-- 0 not enabled; 1 enabled -->
		<param name="machine_bits" value="64"/>
		<param name="virtual_address_width" value="64"/>
		<param name="physical_address_width" value="52"/>
		<param name="virtual_memory_page_size" value="4096"/>
		<stat name="total_cycles" value="%i"/>
		<stat name="idle_cycles" value="%i"/>
		<stat name="busy_cycles"  value="%i"/>
			<!--This page size(B) is complete different from the page size in Main memo secction. this page size is the size of
			virtual memory from OS/Archi perspective; the page size in Main memo secction is the actuall physical line in a DRAM bank  -->
		<!-- *********************** cores ******************* -->
		<component id="system.core" name="core">
		<!-- Core property -->
			<param name="clock_rate" value='%i'/>
			<param name="vdd" value="%f"/><!-- 0 means using ITRS default vdd -->
			<param name="opt_local" value="1"/>
			<param name="instruction_length" value="32"/>
			<param name="opcode_width" value="16"/>
			<!-- address width determins the tag_width in Cache, LSQ and buffers in cache controller
			default value is machine_bits, if not set -->
			<param name="machine_type" value="%i"/><!-- 1 inorder; 0 OOO-->
			<!-- inorder/OoO -->
			<param name="number_hardware_threads" value="1"/>
			<!-- number_instruction_fetch_ports(icache ports) is always 1 in single-thread processor,
			it only may be more than one in SMT processors. BTB ports always equals to fetch ports since
			branch information in consective branch instructions in the same fetch group can be read out from BTB once.-->
			<param name="fetch_width" value="%d"/>
			<!-- fetch_width determins the size of cachelines of L1 cache block -->
			<param name="number_instruction_fetch_ports" value="1"/>
			<param name="decode_width" value="%d"/>
			<!-- decode_width determins the number of ports of the
			renaming table (both RAM and CAM) scheme -->
			<param name="x86" value="1"/>
			<param name="micro_opcode_width" value="8"/>
			<param name="issue_width" value="%u"/>
			<param name="peak_issue_width" value="%u"/>
			<!-- issue_width determins the number of ports of Issue window and other logic
				as in the complexity effective proccessors paper; issue_width==dispatch_width -->
			<param name="commit_width" value="%u"/>
			<!-- commit_width determins the number of ports of register files -->
			<param name="fp_issue_width" value="2"/>
			<param name="prediction_width" value="1"/>
			<!-- number of branch instructions can be predicted simultannouesl-->
			<!-- Current version of McPAT does not distinguish int and floating point pipelines
			Theses parameters are reserved for future use.-->
			<param name="pipelines_per_core" value="1,1"/>
			<!--integer_pipeline and floating_pipelines, if the floating_pipelines is 0, then the pipeline is shared-->
			<param name="pipeline_depth" value="14,14"/>
			<!-- pipeline depth of int and fp, if pipeline is shared, the second number is the average cycles of fp ops -->
			<!-- issue and exe unit-->
			<param name="ALU_per_core" value="%u"/>
			<param name="MUL_per_core" value="1"/>
			<!-- In superscalar processors, usually all ALU are not the same. certain inst. can only
			be processed by certain ALU. However, current McPAT does not consider this subtle difference -->
			<param name="FPU_per_core" value="2"/>
			<!-- buffer between IF and ID stage -->
			<param name="instruction_buffer_size" value="32"/>
			<!-- buffer between ID and sche/exe stage -->
			<param name="decoded_stream_buffer_size" value="16"/>
			<param name="instruction_window_scheme" value="1"/><!-- 0 PHYREG based, 1 RSBASED-->
			<!-- McPAT support 2 types of OoO cores, RS based and physical reg based-->
			<param name="instruction_window_size" value="36"/>
			<param name="fp_instruction_window_size" value="0"/>
			<!-- the instruction issue Q as in Alpha 21264; The RS as in Intel P6 -->
			<param name="ROB_size" value="%d"/>
			<!-- each in-flight instruction has an entry in ROB -->
			<!-- registers -->
			<param name="archi_Regs_IRF_size" value="16"/>
			<param name="archi_Regs_FRF_size" value="32"/>
			<!--  if OoO processor, phy_reg number is needed for renaming logic,
			renaming logic is for both integer and floating point insts.  -->
			<param name="phy_Regs_IRF_size" value="256"/>
			<param name="phy_Regs_FRF_size" value="256"/>
			<!-- rename logic -->
			<param name="rename_scheme" value="0"/>
			<!-- can be RAM based(0) or CAM based(1) rename scheme
			RAM-based scheme will have free list, status table;
			RAM-based scheme have the valid bit in the data field of the CAM
			both RAM and CAM need RAM-based checkpoint table, checkpoint_depth=# of in_flight instructions;
			Detailed RAT Implementation see TR -->
			<param name="register_windows_size" value="0"/>
			<!-- how many windows in the windowed register file, sun processors;
			no register windowing is used when this number is 0 -->
			<!-- In OoO cores, loads and stores can be issued whether inorder(Pentium Pro) or (OoO)out-of-order(Alpha),
			They will always try to exeute out-of-order though. -->
			<param name="LSU_order" value="inorder"/>
			<param name="store_buffer_size" value="96"/>
			<!-- By default, in-order cores do not have load buffers -->
			<param name="load_buffer_size" value="48"/>
			<!-- number of ports refer to sustainable concurrent memory accesses -->
			<param name="memory_ports" value="1"/>
			<!-- max_allowed_in_flight_memo_instructions determins the # of ports of load and store buffer
			as well as the ports of Dcache which is connected to LSU -->
			<!-- dual-pumped Dcache can be used to save the extra read/write ports -->
			<param name="RAS_size" value="64"/>
			<!-- general stats, defines simulation periods;require total, idle, and busy cycles for senity check  -->
			<!-- please note: if target architecture is X86, then all the instrucions refer to (fused) micro-ops -->
			<stat name="total_instructions" value="%i"/>
			<stat name="int_instructions" value="%i"/>
			<stat name="fp_instructions" value="%i"/>
			<stat name="branch_instructions" value="%i"/>
			<stat name="branch_mispredictions" value="%i"/>
			<stat name="load_instructions" value="%i"/>
			<stat name="store_instructions" value="%i"/>
			<stat name="committed_instructions" value="%i"/>
			<stat name="committed_int_instructions" value="%i"/>
			<stat name="committed_fp_instructions" value="%i"/>
			<stat name="total_cycles" value="%i"/>
			<stat name="idle_cycles" value="%i"/>
			<stat name="busy_cycles"  value="%i"/>
			<!-- instruction buffer stats -->
			<!-- ROB stats, both RS and Phy based OoOs have ROB
			performance simulator should capture the difference on accesses,
			otherwise, McPAT has to guess based on number of commited instructions. -->
			<stat name="ROB_reads" value="%i"/>
			<stat name="ROB_writes" value="%i"/>
			<!-- RAT accesses -->
			<stat name="rename_reads" value="%i"/>
			<stat name="rename_writes" value="%i"/>
			<stat name="fp_rename_reads" value="%i"/>
			<stat name="fp_rename_writes" value="%i"/>
			<!-- decode and rename stage use this, should be total ic - nop -->
			<!-- Inst window stats -->
			<stat name="inst_window_reads" value="%i"/>
			<stat name="inst_window_writes" value="%i"/>
			<stat name="inst_window_wakeup_accesses" value="%i"/>
			<stat name="fp_inst_window_reads" value="%i"/>
			<stat name="fp_inst_window_writes" value="%i"/>
			<stat name="fp_inst_window_wakeup_accesses" value="%i"/>
			<!--  RF accesses -->
			<stat name="int_regfile_reads" value="%i"/>
			<stat name="float_regfile_reads" value="%i"/>
			<stat name="int_regfile_writes" value="%i"/>
			<stat name="float_regfile_writes" value="%i"/>
			<!-- accesses to the working reg -->
			<stat name="function_calls" value="%i"/>
			<stat name="context_switches" value="0"/>
			<!-- Number of Windowes switches (number of function calls and returns)-->
			<!-- Alu stats by default, the processor has one FPU that includes the divider and
			 multiplier. The fpu accesses should include accesses to multiplier and divider  -->
			<stat name="ialu_accesses" value="%i"/>
			<stat name="fpu_accesses" value="%i"/>
			<stat name="mul_accesses" value="%i"/>
			<stat name="cdb_alu_accesses" value="%i"/>
			<stat name="cdb_mul_accesses" value="%i"/>
			<stat name="cdb_fpu_accesses" value="%i"/>
			<!-- multiple cycle accesses should be counted multiple times,
			otherwise, McPAT can use internal counter for different floating point instructions
			to get final accesses. But that needs detailed info for floating point inst mix -->
			<!--  currently the performance simulator should
			make sure all the numbers are final numbers,
			including the explicit read/write accesses,
			and the implicite accesses such as replacements and etc.
			Future versions of McPAT may be able to reason the implicite access
			based on param and stats of last level cache
			The same rule applies to all cache access stats too!  -->
			<stat name="IFU_duty_cycle" value="0.25"/>
			<stat name="LSU_duty_cycle" value="0.25"/>
			<stat name="MemManU_I_duty_cycle" value="0.25"/>
			<stat name="MemManU_D_duty_cycle" value="0.25"/>
			<stat name="ALU_duty_cycle" value="1"/>
			<stat name="MUL_duty_cycle" value="0.3"/>
			<stat name="FPU_duty_cycle" value="0.3"/>
			<stat name="ALU_cdb_duty_cycle" value="1"/>
			<stat name="MUL_cdb_duty_cycle" value="0.3"/>
			<stat name="FPU_cdb_duty_cycle" value="0.3"/>
			<param name="number_of_BPT" value="2"/>
			<component id="system.core.predictor" name="PBT">
				<!-- branch predictor; tournament predictor see Alpha implementation -->
				<param name="local_predictor_size" value="10,3"/>
				<param name="local_predictor_entries" value="1024"/>
				<param name="global_predictor_entries" value="4096"/>
				<param name="global_predictor_bits" value="2"/>
				<param name="chooser_predictor_entries" value="4096"/>
				<param name="chooser_predictor_bits" value="2"/>
			</component>
			<component id="system.core.itlb" name="itlb">
				<param name="number_entries" value="128"/>
				<stat name="total_accesses" value="%i"/>
				<stat name="total_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
				<!-- there is no write requests to itlb although writes happen to itlb after miss,
				which is actually a replacement -->
			</component>
			<component id="system.core.icache" name="icache">
				<!-- there is no write requests to itlb although writes happen to it after miss,
				which is actually a replacement -->
				<param name="icache_config" value="%i,%i,%i,%i,%i,%i, %i, %i"/>
				<!-- the parameters are capacity, block_width, associativity, bank, throughput w.r.t. core clock, latency w.r.t. core clock,output_width, cache policy-->
    			<!-- cache_policy;//0 no write or write-though with non-write allocate;1 write-back with write-allocate -->
				<param name="buffer_sizes" value="16, 16, 16, 0"/>
				<!-- cache controller buffer sizes: miss_buffer_size(MSHR),fill_buffer_size,prefetch_buffer_size,wb_buffer_size-->
				<stat name="read_accesses" value="%i"/>
				<stat name="read_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
			</component>
			<component id="system.core.dtlb" name="dtlb">
				<param name="number_entries" value="256"/>
				<stat name="total_accesses" value="%i"/>
				<stat name="total_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
			</component>
			<component id="system.core.dcache" name="dcache">
				<!-- all the buffer related are optional -->
				<param name="dcache_config" value="%i,%i,%i,%i,%i,%i, %i, %i"/>
				<param name="buffer_sizes" value="16, 16, 16, 16"/>
				<!-- cache controller buffer sizes: miss_buffer_size(MSHR),fill_buffer_size,prefetch_buffer_size,wb_buffer_size-->
				<stat name="read_accesses" value="%i"/>
				<stat name="write_accesses" value="%i"/>
				<stat name="read_misses" value="%i"/>
				<stat name="write_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
			</component>
			<component id="system.core.BTB" name="BTB">
				<!-- all the buffer related are optional -->
				<param name="BTB_config" value="18944,8,4,1, 1,3"/>
				<stat name="read_accesses" value="%i"/>
				<stat name="write_accesses" value="0"/>
				<!-- the parameters are capacity,block_width,associativity,bank, throughput w.r.t. core clock, latency w.r.t. core clock,-->
			</component>
		</component>
		<!--**********************************************************************-->
		<component id="system.L20" name="L20">
				<param name="L2_config" value="%i,%i,%i,%i,%i,%i, %i, %i"/>
				<!-- the parameters are capacity,block_width, associativity, bank, throughput w.r.t. core clock, latency w.r.t. core clock,output_width, cache policy -->
				<param name="buffer_sizes" value="16, 16, 16, 16"/>
				<param name="clockrate" value="%i"/>
				<param name="vdd" value="%f"/><!-- 0 means using ITRS default vdd -->
				<param name="ports" value="1,1,1"/>
				<param name="device_type" value="0"/>
				<stat name="read_accesses" value="%i"/>
				<stat name="write_accesses" value="%i"/>
				<stat name="read_misses" value="%i"/>
				<stat name="write_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
				<stat name="duty_cycle" value="%f"/>
		</component>
		<component id="system.L30" name="L30">
				<param name="L3_config" value="%i,%i,%i, %i, %i, %i,%i"/>
				<!-- the parameters are capacity,block_width, associativity,bank, throughput w.r.t. core clock, latency w.r.t. core clock,-->
				<param name="clockrate" value="%i"/>
				<param name="vdd" value="%f"/><!-- 0 means using ITRS default vdd -->
				<param name="ports" value="1,1,1"/>
				<param name="device_type" value="0"/>
				<param name="buffer_sizes" value="16, 16, 16, 16"/>
				<!-- cache controller buffer sizes: miss_buffer_size(MSHR),fill_buffer_size,prefetch_buffer_size,wb_buffer_size-->
				<stat name="read_accesses" value="%i"/>
				<stat name="write_accesses" value="%i"/>
				<stat name="read_misses" value="%i"/>
				<stat name="write_misses" value="%i"/>
				<stat name="conflicts" value="0"/>
				<stat name="duty_cycle" value="%f"/>
		</component>
			<!--**********************************************************************-->
		<component id="system.NoC0" name="noc0">
			<param name="clockrate" value="%i"/>
			<param name="vdd" value="%f"/><!-- 0 means using ITRS default vdd -->
			<param name="type" value="%d"/>
			<!--0:bus, 1:NoC , for bus no matter how many nodes sharing the bus at each time only one node can send req -->
			<param name="horizontal_nodes" value="1"/>
			<param name="vertical_nodes" value="1"/>
			<param name="has_global_link" value="0"/>
			<param name="link_throughput" value="1"/>
			<param name="link_latency" value="1"/>
			<param name="input_ports" value="1"/>
			<param name="output_ports" value="1"/>
			<param name="flit_bits" value="256"/>
			<param name="chip_coverage" value="1"/>
			<param name="link_routing_over_percentage" value="0.5"/>
			<stat name="total_accesses" value="%i"/>
			<stat name="duty_cycle" value="%f"/>
		</component>
			<!--**********************************************************************-->
		<component id="system.mc" name="mc">
			<!-- current version of McPAT uses published values for base parameters of memory controller
			improvments on MC will be added in later versions. -->
			<param name="mc_clock" value="200"/><!--MHz-->
			<param name="vdd" value="0"/><!-- 0 means using ITRS default vdd -->
			<param name="peak_transfer_rate" value="3200"/>
			<param name="block_size" value="64"/><!--B-->
			<param name="number_mcs" value="0"/>
			<!-- current McPAT only supports homogeneous memory controllers -->
			<param name="memory_channels_per_mc" value="1"/>
			<param name="number_ranks" value="2"/>
			<param name="withPHY" value="0"/>
			<param name="req_window_size_per_channel" value="32"/>
			<param name="IO_buffer_size_per_channel" value="32"/>
			<param name="databus_width" value="128"/>
			<param name="addressbus_width" value="51"/>
			<!-- McPAT will add the control bus width to the addressbus width automatically -->
			<stat name="memory_accesses" value="%i"/>
			<stat name="memory_reads" value="%i"/>
			<stat name="memory_writes" value="%i"/>
			<!-- McPAT does not track individual mc, instead, it takes the total accesses and calculate
			the average power per MC or per channel. This is sufficent for most application.
			Further trackdown can be easily added in later versions. -->
		</component>
		<component id="system.niu" name="niu">
			<param name="type" value="0"/> <!-- 1: low power; 0 high performance -->
			<param name="clockrate" value="350"/>
			<param name="vdd" value="0"/><!-- 0 means using ITRS default vdd -->
			<param name="number_units" value="0"/> <!-- unlike PCIe and memory controllers, each Ethernet controller only have one port -->
			<stat name="duty_cycle" value="1.0"/> <!-- achievable max load <= 1.0 -->
			<stat name="total_load_perc" value="0.7"/> <!-- ratio of total achived load to total achivable bandwidth  -->
		</component>
		<component id="system.pcie" name="pcie">
			<!-- On chip PCIe controller, including Phy-->
			<param name="type" value="0"/> <!-- 1: low power; 0 high performance -->
			<param name="withPHY" value="1"/>
			<param name="clockrate" value="350"/>
			<param name="vdd" value="0"/><!-- 0 means using ITRS default vdd -->
			<param name="number_units" value="0"/>
			<param name="num_channels" value="8"/> <!-- 2 ,4 ,8 ,16 ,32 -->
			<stat name="duty_cycle" value="1.0"/> <!-- achievable max load <= 1.0 -->
			<stat name="total_load_perc" value="0.7"/> <!-- Percentage of total achived load to total achivable bandwidth  -->
		</component>
		<component id="system.flashc" name="flashc">
			<param name="number_flashcs" value="0"/>
			<param name="type" value="1"/> <!-- 1: low power; 0 high performance -->
			<param name="withPHY" value="1"/>
			<param name="peak_transfer_rate" value="200"/><!--Per controller sustainable reak rate MB/S -->
			<param name="vdd" value="0"/><!-- 0 means using ITRS default vdd -->
			<stat name="duty_cycle" value="1.0"/> <!-- achievable max load <= 1.0 -->
			<stat name="total_load_perc" value="0.7"/> <!-- Percentage of total achived load to total achivable bandwidth  -->
		</component>"""
xml_template_end = """
		<!--**********************************************************************-->
	</component>
</component>"""

xml_template_customized = """"""

parser = argparse.ArgumentParser(
    description="A script to generate McPAT template for a given configuration",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--customize_component_config",
    "-cc",
    type=str,
    required=False,
    help="Customized module name",
)

output_file = "template_parser.xml"

args = parser.parse_args()
if args.customize_component_config:
    with open(args.customize_component_config, "r") as f:
        data = yaml.safe_load(f)
        component_name = data["component_name"]
        component_id = "system." + component_name
        static_ = data["static"]
        switch_ = data["switch"]
        frequency_ = data["frequency"]
        activation_factor_ = data["activation_factor"]
        switch_count_ = data["switch_count"]
        interval_ = data["interval"]
        xml_template_customized = f"""
        <component id="{component_id}" name="{component_name}">
            <param name="static" value="{static_}"/>
            <param name="switch" value="{switch_}"/>
            <stat name="frequency" value="{frequency_}"/>
            <stat name="activation_factor" value="{activation_factor_}"/>
            <stat name="switch_count" value="{switch_count_}"/>
            <stat name="interval" value="{interval_}"/>
        </component>"""


xml_template = (
    xml_template_root
    + xml_template_system
    + xml_template_customized
    + xml_template_end
)

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, output_file)

with open(file_path, "w") as f:
    f.write(xml_template)
