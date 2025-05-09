#!/bin/csh -fv

#*****************************************************************
# Create, setup, build, & run CESM2 case
#
# Usage:
#	./create_cesm_run_N1_LM.csh
#
# Notes:
# 	Pre-industrial everything, winds are historical, with less melt modifications
# 	Initialized from CESM2less melt B1850 year 1181
#****************************************************************

## Set option variables in this section
# Set case parameters & name
set CASETITLE=PiC_UVnudge_LM
set RES=f09_g17
set COMPSET=B1850cmip6
set COMPSET_SHORT=b
set STARTDATE=1950-01-01

set REFCASE=${COMPSET_SHORT}.e21.B1850.${RES}.CMIP6-piControl.001_branch2
set REFDATE=1181-01-01

set PROJ=$PROJECT
echo $PROJ
set CONT_RUN=FALSE

## Set path variables in this section
set CESMDIR=/glade/work/glydia/cesm_tags/cesm2.1.5
set MODSDIR=/glade/u/home/glydia/mods

# Set array variables for looping through ensemble members
set NNN_arr=( 001 002 003 )
set ptlm_arr=( 0 1.0e-14 2.0e-14 )

## Loop through all ensemble members
foreach i ( 1 2 3 )

	## Set option variables specific to ensemble member
	# Set ensemble number case name
	set NNN=$NNN_arr[$i]
	set CASENAME=${COMPSET_SHORT}.e21.${COMPSET}.${RES}.${CASETITLE}.${NNN}
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
		./xmlchange STOP_OPTION="nyears",RESUBMIT=0,STOP_N=2,JOB_WALLCLOCK_TIME=11:57:00,REST_N=2,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
		./xmlquery STOP_OPTION,RESUBMIT,STOP_N,JOB_WALLCLOCK_TIME,REST_N,REST_OPTION,CONTINUE_RUN

		# Any other xmlchanges...
		./xmlchange RUN_TYPE=hybrid,RUN_REFCASE=$REFCASE,RUN_REFDATE=$REFDATE,GET_REFCASE=FALSE,CLM_NAMELIST_OPTS='',RUN_STARTDATE=$STARTDATE
		./xmlquery RUN_TYPE,RUN_REFCASE,RUN_REFDATE,RUN_STARTDATE

		./xmlchange CICE_MXBLCKS=2,CICE_BLCKX=5,CICE_BLCKY=96,CICE_DECOMPTYPE="cartesian",CICE_DECOMPSETTING="slenderX2"
		./xmlquery CICE_AUTO_DECOMP,CICE_MXBLCKS,CICE_BLCKX,CICE_BLCKY,CICE_DECOMPTYPE,CICE_DECOMPSETTING

		## Setup case
		./case.setup

		./preview_namelists

		# Copy source mods - if any
		#cp $MODSDIR/ocn_mod/* $CASEDIR/SourceMods/src.pop/

		# Copy restart files
		cp /glade/campaign/cgd/ppc/cesm2_tuned_albedo/$REFCASE/rest/$REFDATE-00000/* /glade/derecho/scratch/$USER/$CASENAME/run/

		## Do NAMELIST modifications here
		cp /glade/u/home/glydia/derecho_case_scripts/namelists/N1_LM/user_nl_cam .
		cp /glade/u/home/glydia/derecho_case_scripts/namelists/N1_LM/user_nl_clm .
		cp /glade/u/home/glydia/derecho_case_scripts/namelists/N1_LM/user_nl_cice .
		cp /glade/u/home/glydia/derecho_case_scripts/namelists/N1_LM/user_nl_pop .

		## If not the 1st ensemble member, then set pertlim value
		if ($i > 1) then
			set ptlm=$ptlm_arr[$i]
			echo $ptlm

			# Do additional NAMELIST modifications
			cat >> user_nl_cam << EOFcam

pertlim = $ptlm
EOFcam
		endif

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
		./xmlquery JOB_QUEUE,JOB_WALLCLOCK_TIME
		./xmlchange JOB_WALLCLOCK_TIME=11:57:00
		./xmlquery JOB_QUEUE,JOB_WALLCLOCK_TIME

		# Do XMLCHANGE options for CONTINUE_RUN - 72 years - adjust stop_n/rest_n/resubmit based on 
		./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,CONTINUE_RUN
		./xmlchange STOP_N=6,STOP_OPTION="nyears",RESUBMIT=11,REST_N=6,REST_OPTION="nyears",CONTINUE_RUN=$CONT_RUN
		./xmlquery STOP_N,STOP_OPTION,RESUBMIT,REST_N,REST_OPTION,CONTINUE_RUN

		./case.submit

	endif

end
