import re
from lxml import etree
from copy import deepcopy
from ASTParser import *
import pandas as pd

class CheckingFF():

    #===========================================================#
    # This class is used to check the consistency of FF between #
    # RTL design and Gate-Level design.                         #
    #===========================================================#

    def __init__(self, gate_ast_path, rtl_ast_path, sig_tree_path):
        self.sig_tree = etree.parse(sig_tree_path)
        self.gate_ast = etree.parse(gate_ast_path)
        self.ast = etree.parse(rtl_ast_path)

        self.rtl_ast_lval, self.gate_level_lval = self._find_assigndly()
        # used to store left signals of every non-blocking assignment in rtl level design.
        # used to store left signals of every non-blocking assignment in gate level design.

        self.gate_level_lval_correct = []
        self.gate_level_lval_naming_with_bracket = []
        self.gate_level_lval_naming_diff = []
        self.gate_level_lval_naming_with_genblk = []
        self.gate_level_lval_naming_reg = []
        self.gate_level_lval_set = set()

        self.sig_match_table = {}

        #self.modifying_sig_name()
        self.checking_in_vcd()


    # Print the number of register signals in both Gate-AST & RTL-AST.
    def _counting_ff(self):
        print("Gate Level Design <assigndly>: "+str(len(self.gate_ast.findall(".//assigndly"))))
        print("RTL Design <assigndly>: "+str(len(self.ast.findall(".//assigndly"))))


    # Check if flip-flops in gate level ast all in the vcd-sig.xml.
    def checking_in_vcd(self,output=False):

        print("Start checking FFs in gate level design...")
        rtl_level_vcd_signal = []
        # Find out all signals in sig.xml.
        for node in self.sig_tree.getroot().findall(".//var"):
            if not node.attrib["hier"] in rtl_level_vcd_signal:
                rtl_level_vcd_signal.append(node.attrib["hier"])


        # Check if a flip-flop in ast.
        for ff in self.gate_level_lval:
            flag = 0
            for sig in rtl_level_vcd_signal:
                #print(sig.split("TOP.ibex_simple_system.u_top.u_ibex_top.")[-1])
                if ff == sig.replace("TOP.ibex_simple_system.u_top.u_ibex_top.",""):
                    flag = flag + 1

            # If the name of the flip-flop cannot be found, report the message
            if not flag:
                if output:
                    print("Cannot find "+ff)
                self.gate_level_lval_naming_diff.append(ff)
            elif flag > 1:
                if output:
                    print("Found Multiple "+ff)
            else:
                if output:
                    print("Successfully found "+ff)
                self.gate_level_lval_correct.append(ff)

        for ff in self.gate_level_lval:
            if "genblk" in ff:
                self.gate_level_lval_naming_with_genblk.append(ff)

        # Put FF in different name into another list.
        for ff in self.gate_level_lval_naming_diff:
            if "[" in ff:
                self.gate_level_lval_naming_with_bracket.append(ff)
                if ff.split("[")[0].endswith("_reg"):
                    self.gate_level_lval_naming_reg.append(ff)
            elif ff.endswith("_reg"):
                self.gate_level_lval_naming_reg.append(ff)



    def checking_in_vcd_2(self,output=False):
        
        print("Start checking FFs in gate level design...")
        rtl_level_vcd_signal = []
        # Find out all signals in sig.xml.
        for node in self.sig_tree.getroot().findall(".//var"):
            if not node.attrib["hier"] in rtl_level_vcd_signal:
                rtl_level_vcd_signal.append(node.attrib["hier"])

        # Check if a flip-flop in ast.
        for ff in self.gate_level_lval_set:
            flag = 0
            for sig in rtl_level_vcd_signal:
                #print(sig.split("TOP.ibex_simple_system.u_top.u_ibex_top.")[-1])
                if ff == sig.replace("TOP.ibex_simple_system.u_top.u_ibex_top.",""):
                    flag = flag + 1


            # If the name of the flip-flop cannot be found, report the message
            if output:
                if not flag:
                    print("Cannot find "+ff)
                elif flag > 1:
                    print("Found Multiple "+ff)
                else:
                    print("Successfully found "+ff)


    def modifying_sig_name(self):
        self.gate_level_lval = [sig.split("_reg[")[0] for sig in self.gate_level_lval]
        self.gate_level_lval = [re.sub(r"genblk\d\.", "", sig) for sig in self.gate_level_lval]
        for lval in self.gate_level_lval:
            self.gate_level_lval_set.add(lval)
    # Find out all the left values of every non-blocking assignment.
    # Put them in a list.
    # Check if they are declared in both Gate-AST & RTL-AST.
    def _find_assigndly(self,output=False):

        rtl_ast_lval = []
        gate_level_lval = []
        # Find all <assigndly> in RTL-AST.
        # Put all left signals of them into a list.
        for node in self.ast.getroot().findall(".//assigndly"):
            if node.getchildren()[1].tag == "varref":
                if not node.getchildren()[1].attrib["name"] in rtl_ast_lval:
                    rtl_ast_lval.append(node.getchildren()[1].attrib["name"])
            else:
                for var in node.getchildren()[1].findall(".//varref"):
                    if not var.attrib["name"] in rtl_ast_lval:
                        rtl_ast_lval.append(var.attrib["name"])

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
            # Check every signal in the list has its own declaration in the ast.
            for sig in gate_level_lval:
                if self.gate_ast.getroot().findall(".//var[@name='"+sig+"']") == []:
                    print("Signal {"+sig+"} is not declared in the Gate Level Design.")
                else:
                    print("Signal {"+sig+"} found successfully!!")

            print(rtl_ast_lval)
            print(gate_level_lval)

        return rtl_ast_lval, gate_level_lval



    def checking_in_gen_block(self):
        ast = ASTParser("ast/Vibex_simple_system.xml")
        gen_blocks = ast._check_gen_block_name() 
        for sig in self.gate_level_lval:
            flag = 0
            for gen in gen_blocks:
                if gen in sig:
                    flag = 1
                    break
            if flag:
                print(sig+": is in gen_block --> "+gen)
            else:
                print(sig+" isn't under any gen_block.")


    def checking_astff_to_gate(self,output=False):
        print("Start checking FFs in rtl level ast...")
        # Check if flip-flops from RTL ast all in the gate level ast.
        for ff in self.rtl_ast_lval:
            flag = 0
            for sig in self.gate_level_lval:
                if sig.split(".")[-1] in ff:
                    flag = flag + 1
            
            # If the name of the flip-flop cannot be found, report the message
            if output:
                if not flag:
                    print("Cannot find "+ff)
                elif flag > 1:
                    print("Found Multiple "+ff)
                else:
                    print("Successfully found "+ff)


    def database_construction(self):
        data = pd.DataFrame(index=self.gate_level_lval)
        data['correct'] = data.index.isin(self.gate_level_lval_correct).astype(int)
        data['with_reg'] = data.index.isin(self.gate_level_lval_naming_reg).astype(int)
        data['with_genblk'] = data.index.isin(self.gate_level_lval_naming_with_genblk).astype(int)
        data['with_bracket'] = data.index.isin(self.gate_level_lval_naming_with_bracket).astype(int)
        data['with_reg_without_bracket'] = data['with_reg'] & (~data['with_bracket'])
        data['without_reg_with_bracket'] = (~data['with_reg']) & data['with_bracket']
        
        data.to_csv("gate_ast_lval_data.csv")
        

    def output_sig_match_table(self):
        rtl_level_vcd_signal = []
        # Find out all signals in sig.xml.
        for node in self.sig_tree.getroot().findall(".//var"):
            if not node.attrib["hier"] in rtl_level_vcd_signal:
                rtl_level_vcd_signal.append(node.attrib["hier"])


        output = pd.DataFrame(index=self.gate_level_lval)

        output["hier"] = [""]*len(self.gate_level_lval)
        output["size"] = [0]*len(self.gate_level_lval)
        #for ff in self.gate_level_lval_set:
        #    for sig in rtl_level_vcd_signal:
        #        if ff == sig.replace("TOP.ibex_simple_system.u_top.u_ibex_top.",""):
        #            output.loc[ff,"hier"] = sig
        #            output.loc[ff,"size"] = self.sig_tree.getroot().find(".//var[@hier='"+sig+"']").attrib["size"]
        output.to_csv("output.csv")

if __name__ == "__main__":

    # Required File Path Setting
    gate_ast_path = "./ast/Vibex_top.xml"
    rtl_ast_path = "./ast/Vibex_simple_system.xml"
    sig_tree_path = "./signal/vcd_sig.xml"

    check = CheckingFF(gate_ast_path,rtl_ast_path,sig_tree_path)

    check._find_assigndly(output=False)
    check.checking_astff_to_gate()
    check.modifying_sig_name()
    check.checking_in_vcd_2()
    check.output_sig_match_table()

