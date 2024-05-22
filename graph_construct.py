from lxml import etree
import json
import copy
import time
start_time = time.time()

class GraphConstruct:
    def __init__(self,new_gate_ast_path,node_data_path,graph_data_path):
        self.graph_data_path = graph_data_path
        self.new_gate_ast = etree.parse(new_gate_ast_path)
        self.data = json.loads(open(node_data_path,"r").read()) 
        self.node_classification_dict = {}
        #[dst,src]
        self.link = []
        self.link_n_wire = []
        self.link_n_gate = []
        num = len(self.data["node_category"]["wire_num_list"]) +\
              len(self.data["node_category"]["input_num_list"]) +\
              len(self.data["node_category"]["ff_num_list"]) +\
              len(self.data["node_category"]["and_num_list"]) +\
              len(self.data["node_category"]["or_num_list"]) +\
              len(self.data["node_category"]["xor_num_list"]) +\
              len(self.data["node_category"]["not_num_list"])
        self.v0_num = num
        self.v1_num = num+1


    def node_classify(self):
        for wire in self.data["node_category"]["wire_num_list"]:
            self.node_classification_dict[wire] = {"type":"wire"}
        for inp in self.data["node_category"]["input_num_list"]:
            self.node_classification_dict[inp] = {"type":"input"}
        for ff in self.data["node_category"]["ff_num_list"]:
            self.node_classification_dict[ff] = {"type":"ff"}
        for gate in self.data["node_category"]["and_num_list"]:
            self.node_classification_dict[gate] = {"type":"and"}
        for gate in self.data["node_category"]["or_num_list"]:
            self.node_classification_dict[gate] = {"type":"or"}
        for gate in self.data["node_category"]["xor_num_list"]:
            self.node_classification_dict[gate] = {"type":"xor"}
        for gate in self.data["node_category"]["not_num_list"]:
            self.node_classification_dict[gate] = {"type":"not"}
        num = len(self.node_classification_dict)
        self.node_classification_dict[self.v0_num] = {"type":"V0"}
        self.node_classification_dict[self.v1_num] = {"type":"V1"}

    def load_model(self):
        self.data = json.loads(open(self.graph_data_path,"r").read())


    # Connect nodes between assignment.
    def assign_connect_node(self):
        for cont in self.new_gate_ast.getroot().findall(".//contassign")+self.new_gate_ast.getroot().findall(".//assigndly"):
            child = [i for i in cont.getchildren()]
            child_struct = [i.tag for i in cont.getchildren()]
            if child_struct == ['concat', 'concat']:
                if len(cont.getchildren()[0].getchildren()) != len(cont.getchildren()[1].getchildren()):
                    print("Error: <concat>s don't match!!")
                    print(etree.tostring(cont))
                else:
                    size = len(cont.getchildren()[0].getchildren())
                    for idx in range(size):
                        if cont.getchildren()[0].getchildren()[idx].tag == "V0":
                            self.link.append([int(cont.getchildren()[1].getchildren()[idx].attrib["node_id"]), self.v0_num])
                        elif cont.getchildren()[0].getchildren()[idx].tag == "V1":
                            self.link.append([int(cont.getchildren()[1].getchildren()[idx].attrib["node_id"]), self.v1_num])
                        elif cont.getchildren()[0].getchildren()[idx].tag == "X":
                            continue
                        else:
                            self.link.append([int(cont.getchildren()[1].getchildren()[idx].attrib["node_id"]), int(cont.getchildren()[0].getchildren()[idx].attrib["node_id"])])


            elif "concat" in child_struct:
                print("Error: <concat> vs bit!")
            else:
                if child[0].tag == "V0":
                    self.link.append([int(cont.getchildren()[1].attrib["node_id"]), self.v0_num])
                elif child[0].tag == "V1":
                    self.link.append([int(cont.getchildren()[1].attrib["node_id"]), self.v1_num])
                elif child[0].tag == "X":
                    pass
                else:
                    self.link.append([int(cont.getchildren()[1].attrib["node_id"]), int(cont.getchildren()[0].attrib["node_id"])])

    def gate_connect_node(self):
        for gate in self.new_gate_ast.getroot().findall(".//and"):
            for inp in gate.getchildren():
                if inp.tag == "V0":
                    self.link.append([int(gate.attrib["node_id"]), self.v0_num])
                elif inp.tag == "V1":
                    self.link.append([int(gate.attrib["node_id"]), self.v1_num])
                elif inp.tag == "X":
                    pass
                else:
                    self.link.append([int(gate.attrib["node_id"]), int(inp.attrib["node_id"])])
        for gate in self.new_gate_ast.getroot().findall(".//or"):
            for inp in gate.getchildren():
                if inp.tag == "V0":
                    self.link.append([int(gate.attrib["node_id"]), self.v0_num])
                elif inp.tag == "V1":
                    self.link.append([int(gate.attrib["node_id"]), self.v1_num])
                elif inp.tag == "X":
                    pass
                else:
                    self.link.append([int(gate.attrib["node_id"]), int(inp.attrib["node_id"])])
        for gate in self.new_gate_ast.getroot().findall(".//xor"):
            for inp in gate.getchildren():
                if inp.tag == "V0":
                    self.link.append([int(gate.attrib["node_id"]), self.v0_num])
                elif inp.tag == "V1":
                    self.link.append([int(gate.attrib["node_id"]), self.v1_num])
                elif inp.tag == "X":
                    pass
                else:
                    self.link.append([int(gate.attrib["node_id"]), int(inp.attrib["node_id"])])
        for gate in self.new_gate_ast.getroot().findall(".//not"):
            for inp in gate.getchildren():
                if inp.tag == "V0":
                    self.link.append([int(gate.attrib["node_id"]), self.v0_num])
                elif inp.tag == "V1":
                    self.link.append([int(gate.attrib["node_id"]), self.v1_num])
                elif inp.tag == "X":
                    pass
                else:
                    self.link.append([int(gate.attrib["node_id"]), int(inp.attrib["node_id"])])

    def wire_eliminate(self):
        self.link_n_wire = copy.deepcopy(self.link)
        size = len(self.data["node_category"]["wire_num_list"])
        reduced = 0
        percentage = 0
        flag = 0
        link_without_wire = []
        for idx in range(len(self.link_n_wire)-1,-1,-1):
            if not (self.link_n_wire[idx][0] in self.data["node_category"]["wire_num_list"] or self.link_n_wire[idx][1] in self.data["node_category"]["wire_num_list"]):
                link_without_wire.append(self.link_n_wire.pop(idx))
            

        for wire in copy.deepcopy(self.data["node_category"]["wire_num_list"]):
            tmp = (connection for connection in copy.deepcopy(self.link_n_wire) if connection[0] == wire)
            new_parent = None
            for link in tmp:
                new_parent = link[1]
                self.link_n_wire.remove(link)
            tmp = (connection for connection in copy.deepcopy(self.link_n_wire) if connection[1] == wire)
            for link in tmp:
                self.link_n_wire.remove(link)
                if new_parent != None:
                    self.link_n_wire.append([link[0],new_parent])

            reduced = reduced + 1
            percentage = reduced / size * 100
            
            if percentage > flag*2:
                print("--- %s seconds ---" % (time.time() - start_time))
                print(str(percentage) + "%")
                flag = flag + 1
        self.link_n_wire = self.link_n_wire + link_without_wire
        self.data["link_n_wire"] = self.link_n_wire

    def gate_eliminate(self):
        self.link_n_gate = copy.deepcopy(self.link_n_wire)
        gate_num_list = self.data["node_category"]["and_num_list"] + self.data["node_category"]["or_num_list"] + self.data["node_category"]["xor_num_list"] + self.data["node_category"]["not_num_list"]
        size = len(gate_num_list)
        reduced = 0
        percentage = 0
        flag = 0
        link_without_gate = []
        for idx in range(len(self.link_n_gate)-1,-1,-1):
            if not (self.link_n_gate[idx][0] in gate_num_list or self.link_n_gate[idx][1] in gate_num_list):
                link_without_gate.append(self.link_n_gate.pop(idx))
            

        for gate in copy.deepcopy(gate_num_list):
            tmp = (connection for connection in copy.deepcopy(self.link_n_gate) if connection[0] == gate)
            new_parent = None
            for link in tmp:
                new_parent = link[1]
                self.link_n_gate.remove(link)
            tmp = (connection for connection in copy.deepcopy(self.link_n_gate) if connection[1] == gate)
            for link in tmp:
                self.link_n_gate.remove(link)
                if new_parent != None:
                    self.link_n_gate.append([link[0],new_parent])

            reduced = reduced + 1
            percentage = reduced / size * 100
            
            if percentage > flag*2:
                print("--- %s seconds ---" % (time.time() - start_time))
                print(str(percentage) + "%")
                flag = flag + 1
        self.link_n_gate = self.link_n_gate + link_without_gate
        self.data["link_n_gate"] = self.link_n_gate

    def check(self):
        c = set()
        for con in self.new_gate_ast.getroot().findall(".//assign"):
            c.add(self.new_gate_ast.getpath(con))
        #print(c)
        for gate in self.new_gate_ast.getroot().findall(".//and"):
            if len(gate.getchildren()) != 2:
                print(etree.tostring(gate))
                print("Error: ANDGate input number error!!")
        for gate in self.new_gate_ast.getroot().findall(".//or"):
            if len(gate.getchildren()) != 2:
                print("Error: ORGate input number error!!")
        for gate in self.new_gate_ast.getroot().findall(".//xor"):
            if len(gate.getchildren()) != 2:
                print("Error: XORGate input number error!!")
        for gate in self.new_gate_ast.getroot().findall(".//not"):
            if len(gate.getchildren()) != 1:
                print("Error: NOTGate input number error!!")

    def check_result(self):
        for link in self.link_n_wire:
            if (link[0] in self.data["node_category"]["wire_num_list"]) or (link[1] in self.data["node_category"]["wire_num_list"]):
                print("Found link with wire!!!")
        for link in self.link_n_gate:
            if (link[0] in self.data["node_category"]["and_num_list"]) or (link[1] in self.data["node_category"]["and_num_list"]):
                print("Found link with and!!!")
        for link in self.link_n_gate:
            if (link[0] in self.data["node_category"]["or_num_list"]) or (link[1] in self.data["node_category"]["or_num_list"]):
                print("Found link with or!!!")
        for link in self.link_n_gate:
            if (link[0] in self.data["node_category"]["xor_num_list"]) or (link[1] in self.data["node_category"]["xor_num_list"]):
                print("Found link with xor!!!")
        for link in self.link_n_gate:
            if (link[0] in self.data["node_category"]["not_num_list"]) or (link[1] in self.data["node_category"]["not_num_list"]):
                print("Found link with not!!!")
        
    def output(self):
        with open(self.graph_data_path, 'w') as fp:
            json.dump(self.data, fp)


if __name__ == "__main__":
    new_gate_ast_path = "./ast/modified_gate_ast.xml"
    node_data_path = "./graph_data/node_data.json"
    graph_data_path = "./graph_data/graph_data.json"

    gc = GraphConstruct(new_gate_ast_path,node_data_path,graph_data_path)
    gc.node_classify()
    gc.assign_connect_node()
    gc.gate_connect_node()
    gc.wire_eliminate()
    #gc.gate_eliminate()
    gc.check_result()
    gc.output()

