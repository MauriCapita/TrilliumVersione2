""" The code can be used for "frequency response analyses" to evaluate the 
motion magnitude from a mechanical unbalance load. It processes and visualize
data from an HDF5 file.
 
It requires as input different parameters:
-	filename : 	    the h5 filename that store analysis results
-	ordinate : 		a flag for magnitude of motion results (RMS, 0-pk or pk-pk)
-	dipl     : 		a flag for the plot of displacement results
-	vel      :  	a flag for the plot of velocity results 
-	acc      :	    a flag for the plot of acceleration results
-	nodelist : 		the list of nodes for which create the graphics 

For more information refer to "SOP.560 Level 3 Forced response analysis".
"""
#--INPUT DATA-----------------------------------------------------------------------------------------------------------------------------------------------
filename = "t30719001_rev000_rfa.h5"                # name of h5 file
ordinate = "RMS"                                    # Flag for RMS, 0-pk or pk-pk magnitude
displ = False                                       # Flag for displacement (True or False)
vel = True                                          # Flag for velocity (True or False)
acc = False                                         # Flag for acceleration (True or False)
nodelist = [99049]                                  # List of nodes which extract graphs
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
import tables
import numpy as np
import matplotlib.pyplot as plt
import math as mt
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
def main(filename=filename, ordinate=ordinate, displ=displ, vel=vel, acc=acc, nodelist=nodelist):
# open file
    h5_file=tables.open_file(filename)
# reduce result table filering only the node in the list    
    if displ:
        displ_table = h5_file.root.NASTRAN.RESULT.NODAL.DISPLACEMENT_CPLX
        my_displ = my_results(nodelist,displ_table)
    if vel:
        vel_table = h5_file.root.NASTRAN.RESULT.NODAL.VELOCITY_CPLX
        my_vel = my_results(nodelist,vel_table)
    if acc:
        acc_table = h5_file.root.NASTRAN.RESULT.NODAL.ACCELERATION_CPLX
        my_acc = my_results(nodelist,acc_table)
# define frequencies for each subcase 
    domain_table = h5_file.root.NASTRAN.RESULT.DOMAINS
    n_sub = n_subcase(domain_table)
    freq_RFA = []
    limiti = []
    for subcase in n_sub:
        my_freq,limits = freq(domain_table,subcase)
        freq_RFA.append(my_freq)
        limiti.append(limits)
# read results and create graphs        
    for node_ID in nodelist:
        for i in range(len(n_sub)):
            if displ:
                dx_m,dx_p,dy_m,dy_p,dz_m,dz_p = c_table(displ_table,node_ID,limiti[i][0],limiti[i][1])
                graph(freq_RFA[i],dx_m,dy_m,dz_m,dx_p,dy_p,dz_p,"displacement",ordinate,node_ID,n_sub[i],"[mm]")
            if vel:
                vx_m,vx_p,vy_m,vy_p,vz_m,vz_p = c_table(vel_table,node_ID,limiti[i][0],limiti[i][1])
                graph(freq_RFA[i],vx_m,vy_m,vz_m,vx_p,vy_p,vz_p,"velocity",ordinate,node_ID,n_sub[i],"[mm/s]")
            if acc:
                ax_m,ax_p,ay_m,ay_p,az_m,az_p = c_table(acc_table,node_ID,limiti[i][0],limiti[i][1])
                graph(freq_RFA[i],ax_m,ay_m,az_m,ax_p,ay_p,az_p,"acceleration",ordinate,node_ID,n_sub[i],"[mm/s$^2$]")
# close file
    h5_file.close()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
# calculate the number of subcase in the job
def n_subcase(domain_table):
    bool_condition = "(ANALYSIS == 5)"
    sub_list = np.unique(domain_table.read_where(bool_condition)['SUBCASE'])
    return(sub_list)
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
# define the arrays of frequencies for each subcase
def freq(domain_table,sub):
    # legge le frequenze della RFA
    bool_condition = "(ANALYSIS == 5) & (SUBCASE == sub) & (MODE == 0) & (TIME_FREQ_EIGR != 0)"
    freq_RFA = domain_table.read_where(bool_condition)
    limiti = [min(freq_RFA ['ID']),max(freq_RFA ['ID'])]
    return (freq_RFA ['TIME_FREQ_EIGR'],limiti)
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
# define the sub-table of results for each node in nodelist
def my_results(nodelist,table):
    bool_condition = ("(ID == %d)" %nodelist[0])
    for i in range(1,len(nodelist)):
        bool_condition = bool_condition + (" | (ID == %d)" %nodelist[i])
    complesso = table.read_where(bool_condition)
    return complesso
#-----------------------------------------------------------------------------------------------------------------------------------------------------------   
def c_table(table,node_ID,minID,maxID):    
    # legge lo spostamento del nodo (in notazione complessa)
    complesso = table.read_where("(ID == node_ID) & (DOMAIN_ID >= minID) & (DOMAIN_ID <= maxID)")
    # converte in notazione polare
    x_mod = np.absolute(complesso['XR'] + 1j*complesso['XI'])
    x_phase = np.angle(complesso['XR'] + 1j*complesso['XI'],deg="True")
    #
    y_mod = np.absolute(complesso['YR'] + 1j*complesso['YI'])
    y_phase = np.angle(complesso['YR'] + 1j*complesso['YI'],deg="True")
    #
    z_mod = np.absolute(complesso['ZR'] + 1j*complesso['ZI'])
    z_phase = np.angle(complesso['ZR'] + 1j*complesso['ZI'],deg="True")
    #
    return (x_mod,x_phase,y_mod,y_phase,z_mod,z_phase)
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
def graph(freq,x_mod,y_mod,z_mod,x_phase,y_phase,z_phase,name,ordinate,ID,sub,unit):    
    plt.clf()                                                                                                                     # clear the current figure
    if ordinate == "RMS":
        cost = mt.sqrt(2)/2
    elif ordinate == "0-pk":
        cost = 1
    elif ordinate == "pk-pk":
        cost = 2
    plt.style.use("seaborn-v0_8-pastel")                                                                                          # style of plot
    plt.subplot(2,1,1)
    plt.plot(freq,x_mod*cost,label = "x")
    plt.plot(freq,y_mod*cost,label = "y")
    plt.plot(freq,z_mod*cost,label = "z")
    plt.legend(loc = "best")
    plt.ylabel('%s$_{%s}$ %s' %(name,ordinate,unit))
    plt.grid(True)
    plt.subplot(2,1,2)
    #plt.ylim(-180,180)
    plt.yticks(range(-720,810,90))
    plt.plot(freq, (np.unwrap(np.radians(x_phase)))*180/np.pi, label="x")
    plt.plot(freq, (np.unwrap(np.radians(y_phase)))*180/np.pi, label="y")
    plt.plot(freq, (np.unwrap(np.radians(z_phase)))*180/np.pi, label="z")
    plt.legend(loc = "best")
    plt.xlabel('freq [Hz]')
    plt.ylabel('phase [°]')
    plt.grid(True)
    #plt.show()
    plt.savefig(name+"_"+str(ID)+"_"+str(sub),bbox_inches='tight',dpi=200)
    myfile_out = open(name+ordinate+"_"+str(ID)+"_"+str(sub)+".txt","w")
    myfile_out.write("%-12s %-12s %-12s %-12s %-12s %-12s %-12s\n" %("freq [Hz]","x "+unit,"x [°]","y "+unit,"y [°]","z "+unit,"z [°]"))
    for i in range(len(freq)):
        myfile_out.write("%+12.5e %+12.5e %+12.5e %+12.5e %+12.5e %+12.5e %+12.5e\n" %(freq[i],x_mod[i],x_phase[i],y_mod[i],y_phase[i],z_mod[i],z_phase[i]))
    myfile_out.close()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()