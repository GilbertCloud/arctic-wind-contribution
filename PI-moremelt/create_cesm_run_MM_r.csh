#!/bin/csh -fv

#*****************************************************************
# Create, setup, build, & run CESM2 case
#
# Usage:
#	./create_cesm_run_MM_r.csh
#
# Notes:
# 	Pre-industrial everything, sea ice modified to be thinner - rsnw
#   Initialized from year 0811 of CESM2-CMIP6 B1850 control
#   Ran this script every 50 years for a total of 400 years
#****************************************************************

## Set option variables in this section
# Set case parameters & name
set CASETITLE=moremelt_rsnw0
set RES=f09_g17
set COMPSET=B1850cmip6
set COMPSET_SHORT=b

set REFCASE=${COMPSET_SHORT}.e21.B1850.${RES}.CMIP6-piControl.001
set REFDATE=0811-01-01
set STARTDATE=0811-01-01

set PROJ=$PROJECT
echo $PROJ
set CONT_RUN=FALSE

## Set path variables in this section
set CESMDIR=/glade/work/glydia/cesm_tags/cesm2.1.5
set MODSDIR=/glade/u/home/glydia/mods

# Set array variables for looping through ensemble members

## Set option variables specific to ensemble member
# Set ensemble number case name
set CASENAME=${COMPSET_SHORT}.e21.${COMPSET}.${RES}.${CASETITLE}.001
echo $CASENAME

# Set case path variable
set CASEDIR=/glade/u/home/glydia/derecho_cases/$CASENAME

## If CONTINUE_RUN is false
if ($CONT_RUN == FALSE) then
	## Create case
	cd $CESMDIR/cime/scripts

	./create_newcase --case $CASEDIR --res $RES --compset $COMPSET --project $PROJ --run-unsupported

	cd $CASEDIR

	## Do XMLCHANGE options here

	# CAM configure options
	#./xmlchange --append CAM_CONFIG_OPTS='cosp'

	# Debug
	#./xmlchange INFO_DBUG=2

	# Optimize run
	cp $MODSDIR/env_mach_pes.xml .
	cp $MODSDIR/env_build.xml .

	# Runtime variables
	./xmlchange STOP_OPTION="nyears",RESUBMIT=0,STOP_N=5,JOB_WALLCLOCK_TIME=10:01:00,REST_N=5,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
	./xmlquery STOP_OPTION,RESUBMIT,STOP_N,JOB_WALLCLOCK_TIME,REST_N,REST_OPTION,CONTINUE_RUN

	# Any other xmlchanges...
	./xmlchange RUN_TYPE=hybrid,RUN_REFCASE=$REFCASE,RUN_REFDATE=$REFDATE,GET_REFCASE=FALSE,CLM_NAMELIST_OPTS='',RUN_STARTDATE=$STARTDATE
	./xmlquery RUN_TYPE,RUN_REFCASE,RUN_REFDATE,RUN_STARTDATE

	./xmlchange CICE_MXBLCKS=2,CICE_BLCKX=5,CICE_BLCKY=96,CICE_DECOMPTYPE="cartesian",CICE_DECOMPSETTING="slenderX2"
	./xmlquery CICE_AUTO_DECOMP,CICE_MXBLCKS,CICE_BLCKX,CICE_BLCKY,CICE_DECOMPTYPE,CICE_DECOMPSETTING

	## Setup case
	./case.setup

	./preview_namelists

	# Copy source mods
	cp $MODSDIR/ice_mod/ice_therm_vertical.F90 $CASEDIR/SourceMods/src.cice/

	# Copy restart files
	cp /glade/derecho/scratch/glydia/$REFCASE/$REFDATE-00000/* /glade/derecho/scratch/$USER/$CASENAME/run/

	## Do NAMELIST modifications here
	cp /glade/u/home/glydia/derecho_case_scripts/namelists/MM_r/user_nl_cam .
	cp /glade/u/home/glydia/derecho_case_scripts/namelists/MM_r/user_nl_clm .
	cp /glade/u/home/glydia/derecho_case_scripts/namelists/MM_r/user_nl_cice .
	cp /glade/u/home/glydia/derecho_case_scripts/namelists/MM_r/user_nl_pop .

	./preview_namelists

	## Build case
	qcmd -- ./case.build

	## Submit case to queue
	./case.submit
endif

## If CONTINUE_RUN is true
if ($CONT_RUN == TRUE) then
	cd $CASEDIR

	# Do XMLCHANGE options for CONTINUE_RUN
	./xmlquery JOB_QUEUE,JOB_WALLCLOCK_TIME,PROJECT
	./xmlchange JOB_WALLCLOCK_TIME=10:01:00,PROJECT=$PROJ
	./xmlquery JOB_QUEUE,JOB_WALLCLOCK_TIME,PROJECT

	# # Do XMLCHANGE options for CONTINUE_RUN - 45 years - adjust stop_n/rest_n/resubmit based on 
	# ./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,CONTINUE_RUN
	# ./xmlchange STOP_N=5,STOP_OPTION="nyears",RESUBMIT=8,REST_N=5,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
	# ./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,REST_OPTION,CONTINUE_RUN
	# ./case.submit

    # # Do XMLCHANGE options for CONTINUE_RUN - 5 years - adjust stop_n/rest_n/resubmit based on 
	# ./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,CONTINUE_RUN
	# ./xmlchange STOP_N=5,STOP_OPTION="nyears",RESUBMIT=0,REST_N=5,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
	# ./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,REST_OPTION,CONTINUE_RUN

	# Do XMLCHANGE options for CONTINUE_RUN - 50 years - adjust stop_n/rest_n/resubmit based on 
	./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,CONTINUE_RUN
	./xmlchange STOP_N=5,STOP_OPTION="nyears",RESUBMIT=9,REST_N=5,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
	./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,REST_OPTION,CONTINUE_RUN

	./case.submit

endif


