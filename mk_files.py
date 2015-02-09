import pandas as pd
import math,sys,time
from pmag import dosundec as sundec
from ipmag import igrf
from datetime import datetime as dt
from to_year_fraction import *
from functools import reduce

##Takes formated CSV and creates and writes a .sam header file and a set of sample files##
##for any number of samples.                                                            ##


#################READ IN FILES####################
class mk_sam():

    def __init__(self):
        #fetching comand line data
        file_name = sys.argv[1]
        self.directory = reduce(lambda x,y: x+'/'+y, [sub for sub in file_name.split('/') if not sub.endswith('.csv')]) + '/'

        #file read in
        self.hdf = pd.read_csv(file_name,header=0,index_col=0,nrows=5,usecols=[0,1])
        self.df = pd.read_csv(file_name,header=6,index_col=1,usecols=[0,1,2,3,4,5,13,14,15,16,17,18,19,20]).transpose()
        self.sdf = pd.read_csv(file_name,header=6,index_col=0,usecols=[1,6,7,8,9,10,11,12]).transpose()

        #variable assignments
        self.file_name = file_name
        self.samples = self.df.keys()
        self.attributes = ['strat_level','core_strike','core_dip','bedding_strike','bedding_dip','mass']
        self.site_values = ['lat','long','mag_dec']


    def main(self):
        ##########Find Calculated Values##################
        for sample in samples:
            #calculate sun_core_strike for all samples
            calc_sundec(sample)

            #calculate IGRF
            calc_IGRF(sample)

            #calculate magnetic declination
            calc_magdec(sample)

        ##########CREATE .SAM HEADER FILE##################
        mk_sam_file()

        ################Create Sample Files#################
        for sample in samples:
            mk_sample_file(sample)
        
        ################Write New Values to .csv###################
        update_csv()

    ##########METHOD THAT CREATES .SAM HEADER FILE##################

    def mk_sam_file(self):
        #setting name
        sam_header = hdf['site_info']['name'] + '\r\n'

        #creating long lat and dec info
        i=1
        for value in site_values:
            sam_header += ' ' + hdf['site_info'][value] + ' '*i
            i += 1
        sam_header = sam_header[0:-i+1]
        sam_header += '\r\n'

        #making writing sample info
        for sample in samples:
            sam_header += df[sample]['site_id'] + sample + '\r\n'

        #creating and writing file
        sam_file = open(directory + df[sample]['site_id'] + '.sam', 'w')
        sam_file.write(sam_header)
        sam_file.close()

    ################METHOD THAT CREATES SAMPLE FILES#################

    def mk_sample_file(sample):
    #assign variables for easy refrence
        site_id = df[sample]['site_id']
        comment = df[sample]['comment']
        if type(df[sample]['runs']) == str:
            runs = df[sample]['runs'].split(';')

        #decide which core_strike to use, default is sun_core_strike but if not supplied 
        #magnetic_core_strike will be used
        if math.isnan(df[sample]['sun_core_strike']):
            df[sample]['core_strike'] = df[sample]['magnetic_core_strike']
        else:
            df[sample]['core_strike'] = df[sample]['sun_core_strike']

        #check for no comment
        if type(comment) != str:
            comment = ''

        #insure input is valid
        assert (len(site_id) <= 4),'Locality ID excedes 4 characters: refer too http://cires.colorado.edu/people/jones.craig/PMag_Formats.html'
        assert (len(comment) <= 255),'Sample comment excedes 255 characters: refer too http://cires.colorado.edu/people/jones.craig/PMag_Formats.html'
        assert (len(sample) <= 9),'Sample name excedes 9 chaaracters: refer too http://cires.colorado.edu/people/jones.craig/PMag_Formats.html'
        
        #write sample name and comment for sample file
        new_file =  site_id + ' '*(4-len(site_id)) + sample + ' ' + comment + '\r\n '

        #write in sample attributes on the second line
        for attribute in attributes:
            if math.isnan(df[sample][attribute]):
                df[sample][attribute] = ''
            df[sample][attribute] = str(float(df[sample][attribute]))


            #attributes must follow standard sam format
            assert (len(df[sample][attribute]) <= 5),'Length of ' + attribute + ' excedes 5 characters: refer too http://cires.colorado.edu/people/jones.craig/PMag_Formats.html'

            new_file += ' ' + ' '*(5-len(df[sample][attribute])) + df[sample][attribute]

        new_file += '\r\n'
        
        #if there are previous sample runs write that to the bottem of the file
        for run in runs:
            new_file += run + '\r\n'
        
        #create and write sample file
        new_file = new_file.rstrip('\r\n') + '\r\n'
        sample_file = open(directory + site_id + sample, 'w')
        sample_file.write(new_file)
        sample_file.close()

    ################METHOD THAT UPDATES CSV FILE#################

    def update_csv():
        csv_file = open(file_name)
        csv_str = ''

        for i in range(6):
            csv_str += csv_file.readline()

        header = csv_file.readline()
        csv_str += header
        header = header.strip('\n').split(',')

        for sample in samples:
            line = csv_file.readline()
            items = line.split(',')
            for i in range(len(items)):
                if i == 1:
                    continue
                elif header[i] == 'calculated_IGRF':
                    if type(df[sample][header[i]]) != str:
                        items[i] = str(list(df[sample][header[i]])).replace(',',';')
                    else:
                        items[i] = str(df[sample][header[i]])
                elif header[i] in df[sample].keys():
                    items[i] = str(df[sample][header[i]])
                elif header[i] in sdf[sample].keys():
                    items[i] = str(sdf[sample][header[i]])
                else:
                    raise KeyError('there is no item: ' + header[i])
            csv_str += reduce(lambda x,y: x + ',' + y, items) + '\n'

        new_csv_file = open(file_name,'w')
        new_csv_file.write(csv_str)
        new_csv_file.close()

    ################METHOD THAT CALCULATES DECLINATION FROM SUN DATA##################

    def calc_sundec(self,sample):
        sundata = {}
        if math.isnan(sdf[sample]['shadow_angle']):
            df[sample]['sun_core_strike'] = float('nan')
        else:
            sundata['date'] = str(int(sdf[sample]['year'])) + ':' + str(int(sdf[sample]['month'])) + ':' + str(int(sdf[sample]['days'])) + ':' + str(sdf[sample]['hours']) + ':' + str(sdf[sample]['minutes'])
            sundata['lat'] = hdf['site_info']['lat']
            sundata['lon'] = hdf['site_info']['long']
            sundata['shadow_angle'] = sdf[sample]['shadow_angle']
            sundata['delta_u'] = sdf[sample]['GMT_offset']
            df[sample]['sun_core_strike'] = round(sundec(sundata),1)

    def calc_IGRF(self,sample):
        if math.isnan(sdf[sample]['year']) or math.isnan(sdf[sample]['month']) or math.isnan(sdf[sample]['days']) or math.isnan(sdf[sample]['hours']) or math.isnan(sdf[sample]['minutes']):
            df[sample]['calculated_IGRF'] = 'insufficient data'
        else:
            if math.isnan(hdf['site_info']['elevation']):
                hdf['site_info']['elevation'] = 0
            date = to_year_fraction(dt(int(sdf[sample]['year']),int(sdf[sample]['month']),int(sdf[sample]['days']),int(sdf[sample]['hours']),int(sdf[sample]['minutes'])))
            df[sample]['calculated_IGRF'] = igrf([date,hdf['site_info']['elevation'],float(hdf['site_info']['lat']),float(hdf['site_info']['long'])])

    def calc_magdec(self,sample):
        if math.isnan(df[sample]['sun_core_strike']) or math.isnan(df[sample]['magnetic_core_strike']):
            df[sample]['calculated_mag_dec'] = 'insufficient data'
        else:
            df[sample]['calculated_mag_dec'] = df[sample]['sun_core_strike'] - df[sample]['magnetic_core_strike']


mk_sam().main()
