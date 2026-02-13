#
# Bolt_connect_rev01.py
#
import py_mentat as pyM
import numpy as np
from tkinter import filedialog as fd
#******************************************************************************************************************************************
def main():       
    #-- input -----------------------------------------------------------------------------------------------------------------------------
    lista = fd.askopenfilenames(title= "Input files:")                                # select bolt01_create.txt, bolt02_create.txt, etc...
    toll_R = 0.5                                                                      # searching radial tolerance
    toll_A = 0.5                                                                      # searching axial tolerance
    #--------------------------------------------------------------------------------------------------------------------------------------
    for bolt in lista:
        RBE_node = []                                                                 # x_RBE | y_RBE | z_RBE | diameter | height
        myfile_in = open(bolt,"r")
        linea = myfile_in.readline()
        name = myfile_in.readline().strip()
    #--------------------------------------------------------------------------------------------------------------------------------------
    # bolt/stud axis
        linea = myfile_in.readline()
        asse_bolt = np.array([0.,0.,0.])
        ortho1 = np.array([0.,0.,0.])
        ortho2 = np.array([0.,0.,0.])
        asse_bolt[0] = float(myfile_in.readline().strip())
        asse_bolt[1] = float(myfile_in.readline().strip())
        asse_bolt[2] = float(myfile_in.readline().strip())
        asse_bolt = asse_bolt/np.linalg.norm(asse_bolt)                           # vector normalization
        if asse_bolt[0] != 0.:
            ortho1[0] = -(asse_bolt[1]+asse_bolt[2])/asse_bolt[0]
            ortho1[1] = 1
            ortho1[2] = 1
        elif asse_bolt[1] != 0.:
            ortho1[0] = 1
            ortho1[1] = -asse_bolt[2]/asse_bolt[1]
            ortho1[2] = 1
        else:
            ortho1[0] = 1
            ortho1[1] = 1
            ortho1[2] = 0
        ortho1 = ortho1/np.linalg.norm(ortho1)                                    # creation of the first axis orthogonal to the bolt/stud
        ortho2 = np.cross(asse_bolt,ortho1)                                       # creation of the second axis orthogonal to the bolt/stud
    #--------------------------------------------------------------------------------------------------------------------------------------
        for i in range(36):
            linea = myfile_in.readline()
        counter = 0
        while 1:
            linea = myfile_in.readline()
            counter +=1
            if not linea:
                break
            temp,temp,temp,x_c,y_c,z_c,Diam,DZ = linea.split(",")
            RBE_node.append([float(x_c),float(y_c),float(z_c),float(Diam),float(DZ),ortho1,ortho2])
        myfile_in.close()
    #--------------------------------------------------------------------------------------------------------------------------------------
        RBE3_connect(name,RBE_node,toll_R,toll_A)
#******************************************************************************************************************************************
def RBE3_connect(name,RBE_node,toll_R,toll_A):
    print("***%s connection started***" %name)
    pyM.py_send("*select_method_user_box")
    pyM.py_send("*select_mode_and")
    pyM.py_send("*select_filter_surface")
    pyM.py_send("*select_clear_nodes")
    pyM.py_send("*system_reset")
    pyM.py_send("*system_cylindrical")
    n_RBE = len(RBE_node)
    for i in range(n_RBE):
        if i != 0 and np.all(RBE_node[i-1][5] == RBE_node[i][5]) and np.all(RBE_node[i-1][6] == RBE_node[i][6]):
            pyM.py_send("*origin_x %f" %RBE_node[i][0])
            pyM.py_send("*origin_y %f" %RBE_node[i][1])
            pyM.py_send("*origin_z %f" %RBE_node[i][2])
        else:
            pyM.py_send("*system_align")
            pyM.py_send("%f %f %f" %(RBE_node[i][0],RBE_node[i][1],RBE_node[i][2]))
            pyM.py_send("%f %f %f" %(RBE_node[i][0]+RBE_node[i][5][0],RBE_node[i][1]+RBE_node[i][5][1],RBE_node[i][2]+RBE_node[i][5][2]))
            pyM.py_send("%f %f %f" %(RBE_node[i][0]+RBE_node[i][6][0],RBE_node[i][1]+RBE_node[i][6][1],RBE_node[i][2]+RBE_node[i][6][2]))
        pyM.py_send("*select_nodes")
        pyM.py_send("%f,%f" %(RBE_node[i][3]/2-toll_R,RBE_node[i][3]/2+toll_R))
        pyM.py_send("0,360")
        pyM.py_send("%f,%f" %(-RBE_node[i][4]-toll_A,RBE_node[i][4]+toll_A))
        pyM.py_send("*edit_rbe3 rbe3_%s_%s" %(name,str(i+1).zfill(3)))
        pyM.py_send("*set_rbe3_ret_coef_def 1")
        pyM.py_send("*set_rbe3_ret_dof_def x")
        pyM.py_send("*set_rbe3_ret_dof_def y")
        pyM.py_send("*set_rbe3_ret_dof_def z")
        pyM.py_send("*add_rbe3_conn_nodes_ac structural")
        pyM.py_send("all_selected")
        pyM.py_send("*select_clear_nodes")
        stringa = "rbe3_nconn_entities(rbe3_%s_%s)" %(name,str(i+1).zfill(3))
        n_nodi = pyM.py_get_int(stringa)
        print(name+"_"+str(i+1).zfill(3),n_nodi)
    pyM.py_send("*system_reset")
    pyM.py_send("*select_reset")
    print("***%s connection completed***" %name)
#******************************************************************************************************************************************
if __name__ == '__main__':    
    pyM.py_connect("",40007)
    main()
    pyM.py_disconnect()