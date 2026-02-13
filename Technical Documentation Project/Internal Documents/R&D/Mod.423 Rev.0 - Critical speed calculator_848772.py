import math
from anastruct import SystemElements
from anastruct import LoadCase, LoadCombination
import numpy as np
def main():
#---constant values--------------------------------------------------------------------------------
    g0 = 9.806  # gravity [m/s²]
#---input/output file------------------------------------------------------------------------------
    my_name = "shaft.txt"
    out = open("critical_speed.txt","w")
#---read input data--------------------------------------------------------------------------------
    shaft,station,mass,bear,E0,rho = read_input(my_name)
#---calculate deflection---------------------------------------------------------------------------
    mass,deformation = deflection(shaft,station,mass,bear,E0,rho,g0)
#---calculate critical speed with Rayleigh's equation----------------------------------------------
    omega1 = rayleigh(mass,g0)
    out.write("Rayleigh's equation: first critical speed (massless shaft) [rpm]\n")
    out.write(str(omega1)+"\n")
#---calculate critical speed with Dunkerly's equation----------------------------------------------
    omega2 = dunkerley(mass,g0)
    out.write("Dunkerly's equation: first critical speed (massless shaft) [rpm]\n")
    out.write(str(omega2)+"\n")
#---calculate shaft critical speed with Rayleigh's equation----------------------------------------
    omega0 = rayleigh(deformation,g0)
    out.write("Rayleigh's equation: first critical speed (only shaft) [rpm]\n")
    out.write(str(omega0)+"\n")
#---calculate critical speed with Dunkerly's equation----------------------------------------------
    omega4 = math.sqrt(1/(1/omega0**2+1/omega2**2))
    out.write("Dunkerly's equation: first critical speed [rpm]\n")
    out.write(str(omega4)+"\n")
    out.close()
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
def deflection(shaft,station,mass,bear,E0,rho,g0):
    myplot = False
    file_out = "static_deflection.txt"
    myfile_out = open(file_out,"w")
#---beam object------------------------------------------------------------------------------------
    beam = SystemElements()
    for i in range(len(shaft)):
        pointA = station[i]
        pointB = station[i+1]
        d = shaft[i][1]
        A0 = (math.pi*d**2)/4
        I0 = (math.pi*d**4)/64
        beam.add_element(location=[pointA, pointB],EA = E0*A0,EI = E0*I0)
#---beam support-----------------------------------------------------------------------------------
    for node in bear:
        beam.add_support_hinged(node_id=node)
#---shaft weight only------------------------------------------------------------------------------
    for i in range(len(shaft)):
        locals()["shaft" + str(i)] = LoadCase("shaft" + str(i))
        d = shaft[i][1]
        A0 = (math.pi*d**2)/4
        locals()["shaft" + str(i)].q_load(q=-rho*g0*A0, element_id=i+1, direction='element')
#---concentrated load------------------------------------------------------------------------------
    for i in range(len(mass)):
        locals()["mass" + str(i)] = LoadCase("mass" + str(i))
        locals()["mass" + str(i)].point_load(node_id=mass[i][0], Fy=-g0*mass[i][1], rotation=0)
#---load combination-------------------------------------------------------------------------------
    comb = LoadCombination('shaft and concentrated masses')
    combC = LoadCombination('concentrated masses')
    combD = LoadCombination('shaft only')
    for i in range(len(shaft)):
        combD.add_load_case(locals()["shaft" + str(i)], 1.0)
        comb.add_load_case(locals()["shaft" + str(i)], 1.0)
    for i in range(len(mass)):
        combC.add_load_case(locals()["mass" + str(i)], 1.0)
        comb.add_load_case(locals()["mass" + str(i)], 1.0)
#---solve------------------------------------------------------------------------------------------
    resultsC = combC.solve(beam,force_linear=True)
    resultsD = combD.solve(beam,force_linear=True)
    results = comb.solve(beam,force_linear=True)
#---plot beam model, reaction force, displacement--------------------------------------------------
    if myplot:
        results["combination"].show_structure()
        results["combination"].show_reaction_force()
        results["combination"].show_displacement()     
#---print reaction forces--------------------------------------------------------------------------
    myfile_out.write("Reaction forces for shaft weight only [N]\n")
    R1 = -resultsD["combination"].get_node_results_system(node_id=bear[0])['Fy']
    R2 = -resultsD["combination"].get_node_results_system(node_id=bear[1])['Fy']
    myfile_out.write(str(R1)+"\n")
    myfile_out.write(str(R2)+"\n")
    myfile_out.write("Reaction forces for concentrated masses [N]\n")
    R1 = -resultsC["combination"].get_node_results_system(node_id=bear[0])['Fy']
    R2 = -resultsC["combination"].get_node_results_system(node_id=bear[1])['Fy']
    myfile_out.write(str(R1)+"\n")
    myfile_out.write(str(R2)+"\n")
    myfile_out.write("Reaction forces for shaft and concentrated masses [N]\n")
    R1 = -results["combination"].get_node_results_system(node_id=bear[0])['Fy']
    R2 = -results["combination"].get_node_results_system(node_id=bear[1])['Fy']
    myfile_out.write(str(R1)+"\n")
    myfile_out.write(str(R2)+"\n")
#---displacement of CG of shaft element (shaft weight only)----------------------------------------
    x = 0.
    distr = []
    deformation = resultsD["combination"].get_node_result_range('uy')
    for i in range(len(shaft)):
        m0 = rho*math.pi/4*shaft[i][1]**2*shaft[i][0]
        y = (deformation[i]+deformation[i+1])/2
        distr.append([0,m0,y,0])
#---displacement of concentrated mass (mass weight only)-------------------------------------------
    i = 0
    for node in mass:
        deltay = float(resultsC["combination"].get_node_results_system(node_id=node[0])['uy'])
        node.append(deltay)
        name = "mass"+str(i)
        deltay = float(resultsC[name].get_node_results_system(node_id=node[0])['uy'])
        node.append(deltay)
        i+=1
#---static deformation-----------------------------------------------------------------------------
    graph = results["combination"].get_node_result_range('uy')
    x = 0.
    myfile_out.write("Static deflection\n")
    myfile_out.write("ID     s [mm]       deltay [mm]\n")
    myfile_out.write("%-6d %-12.3f %-12.8f\n" %(1,1000*x,1000*graph[0]))
    for i in range(len(shaft)):
        x = x+float(shaft[i][0])
        myfile_out.write("%-6d %-12.3f %-12.8f\n" %(i+2,1000*x,1000*graph[i+1]))
    myfile_out.close()
#---return data------------------------------------------------------------------------------------    
    return(mass,distr)
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
def rayleigh(mass,g0):
    num = 0.
    den = 0.
    for point in mass:
        num = num + point[1]*abs(point[2])
        den = den + point[1]*point[2]**2
    omega_crit = math.sqrt(g0*num/den)/math.pi*30.
    return(omega_crit)
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
def dunkerley(mass,g0):
    den = 0.
    for station in mass:
        den = den + abs(station[3])
    omega_crit = math.sqrt(g0/den)/math.pi*30.
    return(omega_crit)
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
def read_input(my_name):
    myfile_in = open(my_name,"r")
#---material properties----------------------------------------------------------------------------
    linea = myfile_in.readline()
    linea = myfile_in.readline()
    linea = myfile_in.readline()
    E0,rho = linea.split()
    E0 = float(E0)*10**9
    rho = float(rho)
#---read bearings----------------------------------------------------------------------------------
    linea = myfile_in.readline()
    bear = []
    while 1:
        linea = myfile_in.readline()
        if linea[0] == "#":
            break
        bear.append(int(linea))     # node ID
#---read concentrated mass-------------------------------------------------------------------------
    linea = myfile_in.readline()
    mass = []
    while 1:
        linea = myfile_in.readline()
        if linea[0] == "#":
            break
        ID,m0 = linea.split()
        ID = int(ID)                # m
        m0 = float(m0)              # kg
        conc = [ID,m0]
        mass.append(conc)   
#---read shaft-------------------------------------------------------------------------------------
    linea = myfile_in.readline()
    shaft = []
    while 1:
        linea = myfile_in.readline()
        if not linea:
            break
        L,d = linea.split()
        L = float(L)/1000.
        d = float(d)/1000.
        shaft_part = [L,d]
        shaft.append(shaft_part)
    myfile_in.close()
#---station----------------------------------------------------------------------------------------
    station = [[0.,0.]]
    l = 0.
    for point in shaft:
        l = l + point[0]
        station.append([l,0.])
    return shaft,station,mass,bear,E0,rho
#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()