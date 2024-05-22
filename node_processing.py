from lxml import etree
import xml.dom.minidom
import json
import copy

class NodeProcessing:
    def __init__(self, gate_ast_path, o_new_gate_ast_path, o_node_data_path):
        self.o_new_gate_ast_path = o_new_gate_ast_path
        self.o_node_data_path = o_node_data_path
        self.gate_ast = etree.parse(gate_ast_path)
        self._modify_sel_number()

        self.tag_as_node = ["and","or","xor","not","cond","concat","extend"]

        self.dtpye_dict = {}
            # {"dtype_id_0" : {"type":dt.attrib['name'],"size":size, "left":left, "right":right},
            #  "dtype_id_1" : {"type":dt.attrib['name'],"size":size, "left":left, "right":right},
            # ... }

        self.var_dict = {} 
            # We can find size, left_bit, right_bit of a varible with its name.
            # { "VARNAME1": {"type": ,"size": ,"left": ,"right": },
            #   "VARNAME2": {"type": ,"size": ,"left": ,"right: },
            # ... }

        self.var_split_dict = {}
            # { "VARNAME1": {2:"VARNAME1[2]", 1:"VARNAME1[1]", 0: "VARNAME1[0]"},
            #   "VARNAME2": {31:"VARNAME2[31]", 30:"VARNAME2[30]", 29: "VARNAME2[29]", ... },
            #   "VARNAME3": {2:"VARNAME3[2]", 1:"VARNAME3[1]" },
            # ... }

        self.bit_num_dict = {}
            # { "VARNAME1[0]": 0,
            #   "VARNAME1[1]": 1,
            # ... }


        self.wire_num_list = []
        self.ff_num_list = []        
        self.and_num_list = []
        self.or_num_list = []
        self.xor_num_list = []
        self.not_num_list = []
        self.input_num_list = []


        # Get FF varible list.
        self.ff_list = self._find_assigndly()

        # Main Task!!!
        self._numbering_nodes()
        print("Splitting gates")
        self._modify_cond()
        self._split_sel()
        self._split_var()
        self._split_not()

        print("Splitting Const.")
        self._modify_const_number()
        self._split_const()

        print("Concat & Extend Reduction.")
        self._concat_reduction()
        self._extend_reduction()
        self._concat_reduction()

        print("Numbering gates.")
        self._numbering_gates()
        self._classify_nodes()
        self.connect_node()

        self.dump_node_data()

        with open(self.o_new_gate_ast_path,"w") as f:
            xml_txt = etree.tostring(self.gate_ast, encoding="utf-8")
            f.write(pretty_print_xml_minidom(xml_txt))

    def dump_node_data(self):
        data = {}
        data["dtpye_dict"] = self.dtpye_dict
        data["var_dict"] = self.var_dict
        data["bit_num_dict"] = self.bit_num_dict
        data["node_category"] = {}
        data["node_category"]["wire_num_list"] = self.wire_num_list 
        data["node_category"]["input_num_list"] = self.input_num_list 
        data["node_category"]["ff_num_list"] = self.ff_num_list 
        data["node_category"]["and_num_list"] = self.and_num_list 
        data["node_category"]["or_num_list"] = self.or_num_list 
        data["node_category"]["xor_num_list"] = self.xor_num_list 
        data["node_category"]["not_num_list"] = self.not_num_list
        with open(self.o_node_data_path, 'w') as fp:
            json.dump(data, fp)


    def print_node_data(self):
        print(len(self.wire_num_list))
        print(len(self.input_num_list))
        print(len(self.ff_num_list))
        print(len(self.and_num_list))
        print(len(self.or_num_list))
        print(len(self.xor_num_list))
        print(len(self.not_num_list))


    # Modified the value of <const> under <sel> from HEX to DEC under Gate-AST.
    def _modify_sel_number(self):
        for sel in self.gate_ast.getroot().findall(".//sel"):
            v_num = sel.find("./const[1]").attrib["name"]
            sel.find("./const[1]").attrib["name"] = modify_verilog_number_format(v_num)
            v_num = sel.find("./const[2]").attrib["name"]
            sel.find("./const[2]").attrib["name"] = modify_verilog_number_format(v_num)
    def _modify_const_number(self):
        for const in self.gate_ast.getroot().findall(".//const"):
            v_num = const.attrib["name"]
            const.attrib["name"] = modify_verilog_number_format_tobinary(v_num)

    # Split <varref>
    def _split_var(self):
        for var in self.gate_ast.getroot().findall(".//varref"):
            var_name = var.attrib["name"]
            if self.var_dict[var_name]["size"] == 1:
                signal = etree.Element('signal')
                signal.attrib["name"] = var_name
                signal.attrib["node_id"] = str(self.bit_num_dict[var_name])
                var.getparent().replace(var,signal)
            else:
                concat = etree.Element('concat')
                concat.attrib["dtype_id"] = var.attrib["dtype_id"]
                for node in list(self.var_split_dict[var_name].values()):
                    signal = etree.SubElement(concat,'signal')
                    signal.attrib["name"] = node
                    #bit_list = list(self.bit_num_dict.keys())
                    signal.attrib["node_id"] = str(self.bit_num_dict[node])
                var.getparent().replace(var,concat)

    # Split Multiple bit <not>
    def _split_not(self):
        for n_gate in self.gate_ast.getroot().findall(".//not/concat"):
            concat = etree.Element('concat')
            concat.attrib["dtype_id"] = n_gate.attrib["dtype_id"]
            for child in n_gate.getchildren():
                not_gate = etree.SubElement(concat,'not')
                not_gate.append(child)
            n_gate.getparent().getparent().replace(n_gate.getparent(),concat)


    # Split <sel>.
    def _split_sel(self):
        for sel in self.gate_ast.getroot().findall(".//sel"):
            var_name = sel.find("./varref").attrib["name"]
            sel_bit = int(sel.find("./const[1]").attrib["name"])
            sel_size = int(sel.find("./const[2]").attrib["name"])

            if sel_size == 1:
                signal = etree.Element('signal')
                start_ele = len(self.var_split_dict[var_name]) - 1 - sel_bit
                sig_name = list(self.var_split_dict[var_name].values())[start_ele]
                signal.attrib["name"] = sig_name
                signal.attrib["node_id"] = str(self.bit_num_dict[sig_name])
                sel.getparent().replace(sel,signal)
            else:
                concat = etree.Element('concat')
                concat.attrib["dtype_id"] = sel.attrib["dtype_id"]
                start_ele = len(self.var_split_dict[var_name]) - 1 - sel_bit
                for node in list(self.var_split_dict[var_name].values())[start_ele :: -1][ :sel_size][::-1]:
                    signal = etree.SubElement(concat,'signal')
                    signal.attrib["name"] = node
                    signal.attrib["node_id"] = str(self.bit_num_dict[node])
                sel.getparent().replace(sel,concat)


    # Split <const> in assignment.
    def _split_const(self):
        for const in self.gate_ast.getroot().findall(".//contassign//const"):
            size = self.dtpye_dict[const.attrib["dtype_id"]]["size"]
            num = const.attrib["name"]
            pos = const.getparent().index(const)
            if len(num) == 1:
                signal = None
                if num[0] == "1":
                    signal = etree.Element('V1')
                elif num[0] == "0":
                    signal = etree.Element('V0')
                elif num[0] == "x":
                    signal = etree.Element('X')
                const.getparent().replace(const,signal)
            else:
                concat = etree.Element('concat')
                concat.attrib["dtype_id"] = const.attrib["dtype_id"]
                for bit in num[::-1]:
                    signal = None
                    if bit == "1":
                        signal = etree.SubElement(concat,'V1')
                    elif num[0] == "0":
                        signal = etree.SubElement(concat,'V0')
                    elif num[0] == "x":
                        signal = etree.SubElement(concat,'X')
                const.getparent().replace(const,concat)
        for const in self.gate_ast.getroot().findall(".//assign//const"):
            size = self.dtpye_dict[const.attrib["dtype_id"]]["size"]
            num = const.attrib["name"]
            pos = const.getparent().index(const)
            if len(num) == 1:
                signal = None
                if num[0] == "1":
                    signal = etree.Element('V1')
                elif num[0] == "0":
                    signal = etree.Element('V0')
                elif num[0] == "x":
                    signal = etree.Element('X')
                const.getparent().replace(const,signal)
            else:
                concat = etree.Element('concat')
                concat.attrib["dtype_id"] = const.attrib["dtype_id"]
                for bit in num[::-1]:
                    signal = None
                    if bit == "1":
                        signal = etree.SubElement(concat,'V1')
                    elif num[0] == "0":
                        signal = etree.SubElement(concat,'V0')
                    elif num[0] == "x":
                        signal = etree.SubElement(concat,'X')
                const.getparent().replace(const,concat)
        for const in self.gate_ast.getroot().findall(".//assigndly//const"):
            size = self.dtpye_dict[const.attrib["dtype_id"]]["size"]
            num = const.attrib["name"]
            pos = const.getparent().index(const)
            if len(num) == 1:
                signal = None
                if num[0] == "1":
                    signal = etree.Element('V1')
                elif num[0] == "0":
                    signal = etree.Element('V0')
                elif num[0] == "x":
                    signal = etree.Element('X')
                const.getparent().replace(const,signal)
            else:
                concat = etree.Element('concat')
                concat.attrib["dtype_id"] = const.attrib["dtype_id"]
                for bit in num[::-1]:
                    signal = None
                    if bit == "1":
                        signal = etree.SubElement(concat,'V1')
                    elif num[0] == "0":
                        signal = etree.SubElement(concat,'V0')
                    elif num[0] == "x":
                        signal = etree.SubElement(concat,'X')
                const.getparent().replace(const,concat)


    # Reduce the redundant <concat>.
    def _concat_reduction(self):
        while ( not self.gate_ast.getroot().find(".//concat/concat") is None):
            target_concat = self.gate_ast.getroot().find(".//concat/concat")
            target_index = target_concat.getparent().index(target_concat)
            for node in target_concat.getchildren()[-1::-1]:
                target_concat.getparent().insert(target_index+1,node)
            target_concat.getparent().remove(target_concat)

    # Reduce the redundant <extend>.
    def _extend_reduction(self):
        #while ( not self.gate_ast.getroot().find(".//extend") is None):
        target_extend = self.gate_ast.getroot().find(".//extend")
        if (target_extend.getchildren()[0].tag == "concat") and (len(target_extend.getchildren()) == 1):
            extend_bit = target_extend.getchildren()[0].getchildren()[0]
            target_extend.getchildren()[0].insert(0,copy.deepcopy(extend_bit))
            target_extend.getparent().replace(target_extend,target_extend.getchildren()[0])

    # Replace <cond> to gates.
    def _modify_cond(self):
        while ( not self.gate_ast.getroot().find(".//cond") is None):
            target_cond = self.gate_ast.getroot().find(".//cond")
            new_cond = etree.Element("or")
            new_cond.attrib["dtype_id"] = target_cond.attrib["dtype_id"]
            and_1 = etree.SubElement(new_cond,"and")
            and_2 = etree.SubElement(new_cond,"and")
            not_c = etree.SubElement(and_2,"not")
            children = target_cond.getchildren()
            and_1.append(copy.deepcopy(children[0]))

            and_1.attrib["dtype_id"] = children[1].attrib["dtype_id"]
            and_2.attrib["dtype_id"] = children[2].attrib["dtype_id"]
            not_c.attrib["dtype_id"] = children[0].attrib["dtype_id"]
            and_1.append(children[1])
            and_2.append(children[2])
            not_c.append(children[0])
            target_cond.getparent().replace(target_cond,new_cond)





    # Fill "bit_num_dict" to give every bit a number.
    def _numbering_nodes(self):
        # Get dtype information from Gate-AST.
        for dt in self.gate_ast.getroot().findall(".//basicdtype"):
            size = 0
            left = None
            right = None
            if "left" in dt.attrib:
                size = int(dt.attrib["left"]) - int(dt.attrib["right"]) + 1
                left = int(dt.attrib["left"])
                right = int(dt.attrib["right"])
            else:
                size = 1
            if size > 1:
                size = size + 1
            elif size < 0:
                size = size - 1
            self.dtpye_dict[dt.attrib["id"]] = {"type":dt.attrib['name'],"size":size, "left":left, "right":right}
        # Fill "var_dict" that record varibles with their size
        # Fill "bit_num_dict" that records bits unfer a varible.
        for var in self.gate_ast.getroot().findall(".//var"):
            name = var.attrib["name"]
            dtype_id = var.attrib["dtype_id"]
            size = self.dtpye_dict[dtype_id]["size"]
            left = self.dtpye_dict[dtype_id]["left"]
            right = self.dtpye_dict[dtype_id]["right"]
            if name in self.ff_list: 
                self.var_dict[name]={"type":"FF","size":size, "left":left, "right":right}
            elif "dir" in var.attrib:
                if var.attrib["dir"] == "input":
                    self.var_dict[name]={"type":"input","size":size, "left":left, "right":right}
                else:
                    self.var_dict[name]={"type":"wire","size":size, "left":left, "right":right}
            else:
                self.var_dict[name]={"type":"wire","size":size, "left":left, "right":right}
            self.var_split_dict[name] = {}
            if left == None:
                left = 0
                right = 0
            if size > 1:
                for idx in range(left,right-1,-1):
                    self.var_split_dict[name][idx] = name + "[" + str(idx) + "]"
            elif size == 1:
                self.var_split_dict[name][left] = name
            elif size < 0:
                for idx in range(left,right+1,1):
                    self.var_split_dict[name][idx] = name + "[" + str(idx) + "]"
            else:
                print("Error")
        # Numbering bit nodes.
        bit_num = 0
        for key in self.var_split_dict:
            for key_2 in self.var_split_dict[key]:
                self.bit_num_dict[self.var_split_dict[key][key_2]] = bit_num
                bit_num = bit_num + 1


    # Give each gate a id.
    def _numbering_gates(self):
        node_num = len(self.bit_num_dict)
        for and_gate in self.gate_ast.getroot().findall(".//and"):
            and_gate.attrib["node_id"] = str(node_num)
            self.and_num_list.append(node_num)
            node_num = node_num + 1
        for or_gate in self.gate_ast.getroot().findall(".//or"):
            or_gate.attrib["node_id"] = str(node_num)
            self.or_num_list.append(node_num)
            node_num = node_num + 1
        for xor_gate in self.gate_ast.getroot().findall(".//xor"):
            xor_gate.attrib["node_id"] = str(node_num)
            self.xor_num_list.append(node_num)
            node_num = node_num + 1
        for not_gate in self.gate_ast.getroot().findall(".//not"):
            not_gate.attrib["node_id"] = str(node_num)
            self.not_num_list.append(node_num)
            node_num = node_num + 1

    # Classify Nodes.
    def _classify_nodes(self):
        for var in self.var_dict:
            if self.var_dict[var]["type"] == "FF":
                for bit in self.var_split_dict[var].values():
                    self.ff_num_list.append(self.bit_num_dict[bit])
            if self.var_dict[var]["type"] == "input":
                for bit in self.var_split_dict[var].values():
                    self.input_num_list.append(self.bit_num_dict[bit])
            if self.var_dict[var]["type"] == "wire":
                for bit in self.var_split_dict[var].values():
                    self.wire_num_list.append(self.bit_num_dict[bit])


    # TODO
    def connect_node(self):
        for cont in self.gate_ast.getroot().findall(".//contassign"):
            child_struct = [i.tag for i in cont.getchildren()]
            if child_struct == ['concat', 'concat']:
                pass 
            elif "concat" in child_struct:
                print("Error: <concat> vs bit!")
            else:
                pass

    def _find_assigndly(self,output=False):

        gate_level_lval = []

        # Find all <assigndly> in Gate-AST.
        # Put all left signals of them into a list.
        for node in self.gate_ast.getroot().findall(".//assigndly"):
            if node.getchildren()[1].tag == "varref":
                if not node.getchildren()[1].attrib["name"] in gate_level_lval:
                    gate_level_lval.append(node.getchildren()[1].attrib["name"])
            else:
                for var in node.getchildren()[1].findall(".//varref"):
                    if not var.attrib["name"] in gate_level_lval:
                        gate_level_lval.append(var.attrib["name"])



        if output:
            print(gate_level_lval)

        return gate_level_lval

def pretty_print_xml_minidom(xml_string):
    dom = xml.dom.minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ")
    pretty_xml = "\n".join(line for line in pretty_xml.split("\n") if line.strip())
    return pretty_xml

def digit_16_to_10(c):
    if c == "a" or c == "A":
        return 10
    elif c == "b" or c == "B":
        return 11
    elif c == "c" or c == "C":
        return 12
    elif c == "d" or c == "D":
        return 13
    elif c == "e" or c == "E":
        return 14
    elif c == "f" or c == "F":
        return 15
    else:
        return int(c)

def digit_16_to_2(c):
    if c == "a" or c == "A":
        return "1010"
    elif c == "b" or c == "B":
        return "1011"
    elif c == "c" or c == "C":
        return "1100"
    elif c == "d" or c == "D":
        return "1101"
    elif c == "e" or c == "E":
        return "1110"
    elif c == "f" or c == "F":
        return "1111"
    elif c == "0":
        return "0000"
    elif c == "1":
        return "0001"
    elif c == "2":
        return "0010"
    elif c == "3":
        return "0011"
    elif c == "4":
        return "0100"
    elif c == "5":
        return "0101"
    elif c == "6":
        return "0110"
    elif c == "7":
        return "0111"
    elif c == "8":
        return "1000"
    elif c == "9":
        return "1001"

def hex_to_binary(number):
    txt = ''
    num_t = number.split("'h")[1]
    for bit in num_t:
        txt = txt + digit_16_to_2(bit)
    return txt

def dec_to_binary(number,size):
    txt = ''
    for bit_pos in range(size-1,-1,-1):
        if number&(bit_pos**2) == (bit_pos**2):
            txt = txt + "1"
        else:
            txt = txt + "0"
    return txt

def modify_verilog_number_format(number):
    num = 0
    if "'h" in number:
        num_t = number.split("'h")[1]
        for exp in range(len(num_t)):
            num = (16 ** exp) * digit_16_to_10(num_t[-1-exp]) + num
        num = str(num)
    elif "'b" in number:
        num = number.split("'b")[1]
    else:
        print("Exception!!")
    return str(num)

def modify_verilog_number_format_tobinary(number):
    num = ''
    if "'h" in number:
        size = int(number.split("'h")[0])
        num_t = number.split("'h")[1]
        for n in num_t:
            num = num + digit_16_to_2(n)
        if size < len(num):
            redundant_bits = len(num) - size
            num = num[redundant_bits:]
        elif size > len(num):
            redundant_bits = size - len(num)
            num = "0"*redundant_bits + num
    elif "'b" in number:
        size = int(number.split("'b")[0])
        num = number.split("'b")[1]
        if size > len(num):
            redundant_bits = size - len(num)
            if "x" in number:
                num = "x"*redundant_bits + num
            else:
                num = "0"*redundant_bits + num
    else:
        print("Exception!!")
    return num


if __name__ == "__main__":
    gate_ast = "./ast/Vibex_top.xml"
    new_gate_path = "./ast/modified_gate_ast.xml"
    node_data_path = "./graph_data/node_data.json"
    nd = NodeProcessing(gate_ast,new_gate_path,node_data_path)


