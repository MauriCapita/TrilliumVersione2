#-------------------------------------------------------------------------
# combine harmonic results saving the maximum element value for each speed
#-------------------------------------------------------------------------
#-READ input.txt----------------------------------------------------------
nomi = open("input.txt")
righe = nomi.readlines()
nomi.close()
file_list = []                                        # list of input file
for filename in righe[3:]:
    if filename[-1] == "\n":
        file_list.append(filename[:-1])
    else:
        file_list.append(filename)
file_out = righe[1][:-1]                              # output file name
#-MAIN PROGRAM------------------------------------------------------------
file_in1 = open(file_list[0],"r")        # open the first file in the list
file1 = file_in1.readlines()          # read and store in a list all lines
file_in1.close()                            # close first file in the list
for nome in file_list[1:]:
    file_in2 = open(nome,"r")           # open the other files in the list
    file2 = file_in2.readlines()      # read and store in a list all lines
    file_in2.close()                                          # close file
    for i in range(14,len(file1)):   # compare stress value and  store max
        if file1[i][0] == " " and file1[i][3] != " ":
            left1 = float(file1[i].split()[2])
            left2 = float(file2[i].split()[2])
            if left2 > left1:
                file1[i] = file2[i]
        elif file1[i][0] == " " and file1[i][3] == " ":
            right1= float(file1[i].split()[0])
            right2= float(file2[i].split()[0])
            if right2 > right1:
                file1[i] = file2[i]
fileout = open(file_out,"w")                       # open the output file
for righe in file1:
    fileout.write(righe)                 # write all the rows in the file
fileout.close()                                   # close the output file