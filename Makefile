NETLIST_PATH := ./netlist/ibex_top.pre_map.v
AST_PATH := ./ast

# Input:  sim.vcd, Vibex_simple_system.xml
# Output: vcd_sig.xml
gen_sig_tree:
	python3 VCDParser.py

# Input:  Vibex_top.xml
# Output: modified_netlist.xml, node_data.json
node:
	python3 node_processing.py


gen_gate_ast:
	verilator --xml-only $(NETLIST_PATH) --Mdir $(AST_PATH) -Wno-LITENDIAN
