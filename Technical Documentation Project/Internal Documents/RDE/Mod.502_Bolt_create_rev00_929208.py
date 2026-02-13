#
# Bolt_create_rev01.py
#
from py_mentat import *
import numpy as np
from tkinter import filedialog as fd
#********************************************************************************************************************************
def main():
    # Input data
    input = fd.askopenfilenames(title= "Input files:")                      # select bolt01_create.txt, bolt02_create.txt, etc...
    for file in input:
        bolt(file)
#********************************************************************************************************************************
def bolt(f_name):
    #----------------------------------------------------------------------------------------------------------------------------
    #---------------------------------------------------------- INPUT -----------------------------------------------------------
    #----------------------------------------------------------------------------------------------------------------------------
    toll = 0.1                      # searching tolerance
    seed_mesh = 4                   # meshseed
    max_ID = 999999999              # ID greater than the max ID of the model
    #----------------------------------------------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------------------------------------------
    # Open input file
    myfile_in = open(f_name,"r")
    #----------------------------------------------------------------------------------------------------------------------------
    # Group name
    myfile_in.readline()
    group_name = myfile_in.readline().strip()
    #----------------------------------------------------------------------------------------------------------------------------  
    # Bolt/stud axis
    myfile_in.readline()
    x_asse = float(myfile_in.readline().strip())
    y_asse = float(myfile_in.readline().strip())
    z_asse = float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Bolt/stud material
    myfile_in.readline()
    mat_name = myfile_in.readline().strip()
    E = float(myfile_in.readline().strip())
    nu = float(myfile_in.readline().strip())
    rho = float(myfile_in.readline().strip())
    Sy = float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Nut material
    myfile_in.readline()
    mat_n_name = myfile_in.readline().strip()
    E_n = float(myfile_in.readline().strip())
    nu_n = float(myfile_in.readline().strip())
    rho_n = float(myfile_in.readline().strip())
    Sy_n = float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer material
    myfile_in.readline()
    mat_r_name = myfile_in.readline()[:-1]
    E_r = float(myfile_in.readline())
    nu_r = float(myfile_in.readline())
    rho_r = float(myfile_in.readline())
    Sy_r = float(myfile_in.readline())
    #----------------------------------------------------------------------------------------------------------------------------
    # Nut dimension
    myfile_in.readline()
    D =  float(myfile_in.readline().strip())
    M =  float(myfile_in.readline().strip())
    p =  float(myfile_in.readline().strip())
    s =  float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Bolt/stud central part dimension
    myfile_in.readline()
    Dg = float(myfile_in.readline().strip())
    Lg = float(myfile_in.readline().strip())
    Ls = float(myfile_in.readline().strip())
    Ltot = float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer dimension
    myfile_in.readline()
    rond_check = myfile_in.readline().strip()
    Dr = float(myfile_in.readline().strip())
    dr = float(myfile_in.readline().strip())
    Lr = float(myfile_in.readline().strip())
    #----------------------------------------------------------------------------------------------------------------------------
    # Bolt/stud position
    center = []
    #----------------------------------------------------------------------------------------------------------------------------
    myfile_in.readline()
    while 1:
        linea = myfile_in.readline()
        if linea: 
            xyz = [float(i) for i in linea.split(",")]
            center.append(xyz)
        if not linea:
            break
    #----------------------------------------------------------------------------------------------------------------------------
    #---------------------------------------------------- STOP READING INPUT ----------------------------------------------------
    #----------------------------------------------------------------------------------------------------------------------------
    # starting ID for nodes and elements
    ID_node_start = py_get_int("max_node_id()")
    ID_ele_start = py_get_int("max_element_id()")
    ID_point_start = py_get_int("max_point_id()")
    ID_curve_start = py_get_int("max_curve_id()")
    ID_surf_start = py_get_int("max_surface_id()")
    #----------------------------------------------------------------------------------------------------------------------------
    # user coordinate system creation in the center of the bolt, oriented with his axis
    x_axes = user_coord(center[0][0],center[0][1],center[0][2],x_asse,y_asse,z_asse)
    #----------------------------------------------------------------------------------------------------------------------------
    # Nut resistant diameter
    d = ((M-0.64952*p)+(M-1.22687*p))/2    
    #----------------------------------------------------------------------------------------------------------------------------
    # Nut material creation
    material(group_name + "_" + mat_n_name,rho_n,E,nu_n,Sy_n)
    #----------------------------------------------------------------------------------------------------------------------------
    # Nut geometric property creation (solid)
    name = group_name + "_nut"
    solid_prop(name)
    #----------------------------------------------------------------------------------------------------------------------------
    # Bolt/stud material creation
    material(group_name + "_" + mat_name,rho,E,nu,Sy)
    #----------------------------------------------------------------------------------------------------------------------------
    # Bolt/stud central part property creation (beam)
    if Lg != 0.:
        name = group_name + "_cyl"
        beam_prop(name,x_axes[0],x_axes[1],x_axes[2],Dg)
    #----------------------------------------------------------------------------------------------------------------------------
    # Screw property creation
    if Ls != 0.:
        name = group_name + "_screw"
        beam_prop(name,x_axes[0],x_axes[1],x_axes[2],d)
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of the central square
    py_send("*set_element_class quad4")
    py_send("*add_elements")
    py_send("*system_cylindrical")
    py_send("node(%f,0.,0.)" %(d/4))
    py_send("node(%f,90.,0.)" %(d/4))
    py_send("node(%f,180.,0.)" %(d/4))
    py_send("node(%f,270.,0.)" %(d/4))
    py_send("*system_rectangular")
    py_send("*prog_param subdivide:ndiv_u %d" %seed_mesh)
    py_send("*prog_param subdivide:ndiv_v %d" %seed_mesh)
    py_send("*subdivide_elements")
    py_send("%d" %(ID_ele_start+1))
    py_send("# | End of List")
    py_send("*system_cylindrical")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of a polyline
    py_send("*set_curve_type polyline")
    py_send("*add_curves")
    py_send("point( %f,0.,0.)" %(d/4))
    py_send("point( %f,90.,0.)" %(d/4))
    py_send("point( %f,180.,0.)" %(d/4))
    py_send("point( %f,270.,0.)" %(d/4))
    py_send("point( %f,0.,0.)" %(d/4))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of a quarter of circle
    py_send("*set_curve_type circle_cr")
    py_send("*add_curves")
    py_send("0.,0.,0.")
    py_send("%f" %(d/2))
    py_send("0.,0.,0.")
    py_send("%f" %(D/2))
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of a surface
    py_send("*set_surface_type ruled")
    py_send("*add_surfaces")
    py_send("%d" %(ID_curve_start+1))
    py_send("%d" %(ID_curve_start+2))
    py_send("%d" %(ID_curve_start+2))
    py_send("%d" %(ID_curve_start+3))
    #----------------------------------------------------------------------------------------------------------------------------
    # Conversion from surface to elements
    py_send("*prog_param convert:ndiv_u %d" %(4*seed_mesh))
    py_send("*prog_param convert:ndiv_v %d" %(seed_mesh/2))
    py_send("*convert_surfaces")
    py_send("%d %d" %(ID_surf_start+1,ID_surf_start+2))
    py_send("# | End of List")
    py_send("*remove_surfaces")
    py_send("%d to %d" %(ID_surf_start+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_curves")
    py_send("%d to %d" %(ID_curve_start+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_points")
    py_send("%d to %d" %(ID_point_start+1,max_ID))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------    
    # Sweep/equivalence of the nodes
    py_send("*prog_option sweep:mode:merge")
    py_send("*sweep_cbody_integrity on")
    py_send("*sweep_nodes")
    py_send("%d to %d" %(ID_node_start+1,max_ID))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Selection of quad elements and extrusion
    py_send("*system_rectangular")
    py_send("*prog_param expand:trans_z %f" %(s/int(16*s/D/3.14)))
    py_send("*prog_param expand:repetitions %f" %(int(16*s/D/3.14)))
    py_send("*expand_elements")
    py_send("%d to %d" %(ID_ele_start+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_unused_nodes")
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to nut material
    py_send("*edit_mater %s" %(group_name + "_" + mat_n_name))
    py_send("*add_mater_elements")
    py_send("%d to %d" %(ID_ele_start+1,max_ID))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to geometric property and creation of the contact body
    py_send("*edit_geometry %s_nut"  %group_name)
    py_send("*add_geometry_elements")
    py_send("%d to %d" %(ID_ele_start+1,max_ID))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of a contact body for the nut
    py_send("*new_cbody mesh *contact_option state:solid *contact_option skip_structural:off")
    py_send("*contact_body_name %s_nut" %group_name)
    py_send("*add_contact_body_elements")
    py_send("%d to %d" %(ID_ele_start+1,max_ID))
    py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Create the lower part of the bolt
    e_temp = py_get_int("max_element_id()")
    py_send("*prog_param duplicate:trans_x 0.")
    py_send("*prog_param duplicate:trans_y 0.")
    py_send("*prog_param duplicate:trans_z %f" %(-Ltot-s))
    py_send("*duplicate_elements")
    py_send("%d to %d" %(ID_ele_start+1,e_temp))
    py_send("# | End of List")
    e_temp0 = py_get_int("max_element_id()")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of the beam elements for the central part of the bolt/stud
    if Lg != 0.:
        py_send("*add_nodes")
        py_send("0.,0.,0.")
        n_temp = py_get_int("max_node_id()")
        e_temp = py_get_int("max_element_id()")               
        py_send("*prog_param expand:trans_z %f " %(-Lg/max(2,int(2*Lg/Dg))))
        py_send("*prog_param expand:repetitions %f" %(max(2,int(2*Lg/Dg))))
        py_send("*expand_nodes")
        py_send("%d" %n_temp)
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to bolt/stud material
        py_send("*edit_mater %s" %(group_name + "_" + mat_name))
        py_send("*add_mater_elements")
        py_send("%d to %d" %(e_temp+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to the central part of the bolt/stud property
        py_send("*edit_geometry %s_cyl"  %(group_name))
        py_send("*add_geometry_elements")
        py_send("%d to %d" %(e_temp+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------   
    # Creation of the beam elements for the screw part of the bolt/stud
    if Ls != 0.:
        n_temp = py_get_int("max_node_id()")
        e_temp = py_get_int("max_element_id()")     
        py_send("*prog_param expand:trans_z %f " %(-Ls/int(2*Ls/d)))
        py_send("*prog_param expand:repetitions %f" %(int(2*Ls/d)))
        py_send("*expand_nodes")
        py_send("%d" %(n_temp))
        py_send("# | End of List")
        py_send("*remove_unused_nodes")
        py_send("*sweep_nodes")
        py_send("%d to %d" %(n_temp,n_temp+1))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to bolt/stud material
        py_send("*edit_mater %s" %(group_name + "_" + mat_name))
        py_send("*add_mater_elements")
        py_send("%d to %d" %(e_temp+1,max_ID))
        py_send("# | End of List")    
    #----------------------------------------------------------------------------------------------------------------------------
    # Assignment to the screw part of the bolt/stud
        py_send("*edit_geometry %s_screw"  %(group_name))
        py_send("*add_geometry_elements")
        py_send("%d to %d" %(e_temp+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of a contact body for the central part of the bolt/stud
    py_send("*new_cbody mesh *contact_option state:solid *contact_option skip_structural:off")
    py_send("*contact_body_name %s_cyl" %group_name)
    py_send("*add_contact_body_elements")
    py_send("%d to %d" %(e_temp0+1,max_ID))
    py_send("# | End of List")  
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation/copy of all the bolt/stud
    e_temp = py_get_int("max_element_id()")
    py_send("*system_reset")
    for i in range(1,len(center)):
        py_send("*prog_param duplicate:trans_x %f" %(center[i][0]-center[0][0]))
        py_send("*prog_param duplicate:trans_y %f" %(center[i][1]-center[0][1]))
        py_send("*prog_param duplicate:trans_z %f" %(center[i][2]-center[0][2]))
        py_send("*duplicate_elements")
        py_send("%d to %d" %(ID_ele_start+1,e_temp))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer creation
    if rond_check == "True":
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer material creation
        material(group_name + "_" + mat_r_name,rho_r,E_r,nu_r,Sy_r)
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer geometric property creation
        name = group_name + "_washer"
        solid_prop(name)
    #----------------------------------------------------------------------------------------------------------------------------
    # user coordinate system creation in the center of the bolt, oriented with his axis
        x_axes = user_coord(center[0][0],center[0][1],center[0][2],x_asse,y_asse,z_asse)
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer creation 
        e_temp_in = py_get_int("max_element_id()")
        washer(Dr,dr,Lr,seed_mesh,ID_point_start,ID_curve_start,ID_surf_start,max_ID)
    #----------------------------------------------------------------------------------------------------------------------------
    # Geometric property
        py_send("*edit_geometry %s_washer"  %(group_name))
        py_send("*add_geometry_elements")
        py_send("%d to %d" %(e_temp_in+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Creation of the washer contact body
        py_send("*new_cbody mesh *contact_option state:solid *contact_option skip_structural:off")
        py_send("*contact_body_name %s_washer" %(group_name))
        py_send("*add_contact_body_elements")
        py_send("%d to %d" %(e_temp_in+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Material assignment
        py_send("*edit_mater %s" %(group_name + "_" + mat_r_name))
        py_send("*add_mater_elements")
        py_send("%d to %d" %(e_temp_in+1,max_ID))
        py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    # Create the lower washer
        e_temp_fin = py_get_int("max_element_id()")
        py_send("*prog_param duplicate:trans_x 0.")
        py_send("*prog_param duplicate:trans_y 0.")
        py_send("*prog_param duplicate:trans_z %f" %(-Ltot+Lr))
        py_send("*duplicate_elements")
        py_send("%d to %d" %(e_temp_in+1,e_temp_fin))
        py_send("# | End of List")   
    #----------------------------------------------------------------------------------------------------------------------------
    # Washer duplication
        e_temp_fin = py_get_int("max_element_id()")
        py_send("*system_reset")
        for i in range(1,len(center)):
            py_send("*prog_param duplicate:trans_x %f" %(center[i][0]-center[0][0]))
            py_send("*prog_param duplicate:trans_y %f" %(center[i][1]-center[0][1]))
            py_send("*prog_param duplicate:trans_z %f" %(center[i][2]-center[0][2]))
            py_send("*duplicate_elements")
            py_send("%d to %d" %(e_temp_in+1,e_temp_fin))
            py_send("# | End of List")
    #----------------------------------------------------------------------------------------------------------------------------
    py_send("*system_reset")
    myfile_in.close()
#********************************************************************************************************************************
def material(name,rho,E,nu,Sy):
    # Elastic-perfectly plastic material creation
    py_send("*new_mater standard *mater_option general:state:solid *mater_option general:skip_structural:off")
    py_send("*mater_name %s" %name)
    py_send("*mater_param general:mass_density %s" %rho)
    py_send("*mater_param structural:youngs_modulus %f" %E)
    py_send("*mater_param structural:poissons_ratio %f" %nu) 
    py_send("*mater_option structural:plasticity:on")
    py_send("*mater_param structural:yield_stress %f" %Sy)
#********************************************************************************************************************************    
def solid_prop(prop_name):
    # Solid properties creation
    py_send("*new_geometry *geometry_type mech_three_solid")
    py_send("*geometry_name %s" %prop_name)
#********************************************************************************************************************************    
def beam_prop(name,x,y,z,D):
    # Beam properties creation
    py_send("*new_geometry *geometry_type mech_three_beam_ela")
    py_send("*geometry_name %s" %name)
    py_send("*geometry_param orientx %f" %x) 
    py_send("*geometry_param orienty %f" %y)
    py_send("*geometry_param orientz %f" %z)
    py_send("*geometry_option section_props:calculated")
    py_send("*geometry_option solid_sect:circular")
    py_send("*geometry_param diameter %f" %D)
    py_send("*geometry_option bm_cont_end_caps:on") 
#********************************************************************************************************************************
def user_coord(x_c,y_c,z_c,x_a,y_a,z_a):
    # Traslate and rotate the reference coordinate system and return a versor orthogonal to the bolt/stud axis 
    asseX = np.array([0.,0.,0.])
    asseY = np.array([0.,0.,0])
    asseZ = np.array([0.,0.,0.])    
    asseZ[0] = x_a
    asseZ[1] = y_a
    asseZ[2] = z_a    
    asseZ = asseZ/np.linalg.norm(asseZ)    
    if asseZ[2] != 0:
        asseX[0] = 1.
        asseX[1] = 0.
        asseX[2] = -asseZ[0]/asseZ[2]
    elif asseZ[1] != 0:
        asseX[0] = 1.
        asseX[1] = -asseZ[0]/asseZ[1]
        asseX[2] = 0.
    else:
        asseX[0] = 0.
        asseX[1] = 1.
        asseX[2] = 0.    
    asseX = asseX/np.linalg.norm(asseX) # asse ortogonale
    asseY = np.cross(asseZ,asseX)    
    py_send("*system_reset")
    py_send("*system_align")
    py_send("%f %f %f" %(x_c,y_c,z_c)) # origine
    py_send("%f %f %f" %(x_c+asseX[0],y_c+asseX[1],z_c+asseX[2])) # punto asse X
    py_send("%f %f %f" %(x_c+asseY[0],y_c+asseY[1],z_c+asseY[2])) # punto asse Y positivo    
    return asseX
#********************************************************************************************************************************
def washer(d,D,s,seed_mesh,ID_point_start,ID_curve_start,ID_surf_start,max_ID):
    # Washer creation
    # Creation of concentric circle
    py_send("*set_curve_type circle_cr")
    py_send("*add_curves")
    py_send("0.,0.,0.")
    py_send("%f" %(d/2))
    py_send("0.,0.,0.")
    py_send("%f" %(D/2))
    # Surface creation
    py_send("*set_surface_type ruled")
    py_send("*add_surfaces")
    py_send("1")
    py_send("2")
    py_send("*prog_param convert:ndiv_u %d" %(4*seed_mesh))
    py_send("*prog_param convert:ndiv_v %d" %(3*seed_mesh/4))
    # Elements creation
    n_temp = py_get_int("max_node_id()")
    e_temp = py_get_int("max_element_id()")
    py_send("*convert_surfaces")
    py_send("1")
    py_send("# | End of List")
    py_send("*remove_surfaces")
    py_send("%d to %d" %(ID_surf_start+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_curves")
    py_send("%d to %d" %(ID_curve_start+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_points")
    py_send("%d to %d" %(ID_point_start+1,max_ID))
    py_send("# | End of List")
    # Node sweep
    py_send("*prog_option sweep:mode:merge")
    py_send("*sweep_cbody_integrity on")
    py_send("*sweep_nodes")
    py_send("%d to %d" %(n_temp+1,max_ID))
    py_send("# | End of List")
    # Elements extrusion
    py_send("*system_rectangular")
    py_send("*prog_param expand:trans_z %f" %(-s/2))
    py_send("*prog_param expand:repetitions 2")
    py_send("*expand_elements")
    py_send("%d to %d" %(e_temp+1,max_ID))
    py_send("# | End of List")
    py_send("*remove_unused_nodes")
#********************************************************************************************************************************
if __name__ == '__main__':
    py_connect("",40007)
    main()
    py_disconnect()
