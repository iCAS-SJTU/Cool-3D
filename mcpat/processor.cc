/*****************************************************************************
 *                                McPAT
 *                      SOFTWARE LICENSE AGREEMENT
 *            Copyright 2012 Hewlett-Packard Development Company, L.P.
 *                          All Rights Reserved
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.

 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.”
 *
 ***************************************************************************/
#include <string.h>
#include <iostream>
#include <stdio.h>
#include <algorithm>
#include <string.h>
#include <cmath>
#include <assert.h>
#include <fstream>
#include "parameter.h"
#include "array.h"
#include "const.h"
#include "basic_circuit.h"
#include "XML_Parse.h"
#include "processor.h"
#include "version.h"


Processor::Processor(ParseXML *XML_interface)
:XML(XML_interface),//TODO: using one global copy may have problems.
 mc(0),
 niu(0),
 pcie(0),
 flashcontroller(0)
{
  int i;
  double pppm_t[4]    = {1,1,1,1};
  set_proc_param();
  if (procdynp.homoCore)
    numCore = procdynp.numCore==0? 0:1;
  else
    numCore = procdynp.numCore;

  if (procdynp.homoL2)
    numL2 = procdynp.numL2==0? 0:1;
  else
    numL2 = procdynp.numL2;

  if (XML->sys.Private_L2 && numCore != numL2)
  {
    cout<<"Number of private L2 does not match number of cores"<<endl;
      exit(0);
  }

  if (procdynp.homoL3)
    numL3 = procdynp.numL3==0? 0:1;
  else
    numL3 = procdynp.numL3;

  if (procdynp.homoNOC)
    numNOC = procdynp.numNOC==0? 0:1;
  else
    numNOC = procdynp.numNOC;

  if (procdynp.homoL1Dir)
    numL1Dir = procdynp.numL1Dir==0? 0:1;
  else
    numL1Dir = procdynp.numL1Dir;

  if (procdynp.homoL2Dir)
    numL2Dir = procdynp.numL2Dir==0? 0:1;
  else
    numL2Dir = procdynp.numL2Dir;

  initialize();
  return;
}

void Processor::initialize(){
    /*
   *  placement and routing overhead is 10%, core scales worse than cache 40% is accumulated from 90 to 22nm
   *  There is no point to have heterogeneous memory controller on chip,
   *  thus McPAT only support homogeneous memory controllers.
   */
  int i;
  double pppm_t[4]    = {1,1,1,1};

  if (XML->sys.number_of_custom_blocks > 0){
    CIM_SRAM.area = XML->sys.CIM_SRAM.area;
    CIM_SRAM.static_power = XML->sys.CIM_SRAM.static_power;
    CIM_SRAM.switching_energy = XML->sys.CIM_SRAM.switch_energy;
  }
  
  for (i = 0;i < numCore; i++){
    cores.push_back(new Core(XML,i, &interface_ip));
    if (procdynp.homoCore){        
      core.area.set_area(core.area.get_area() + cores[i]->area.get_area()*procdynp.numCore);
      area.set_area(area.get_area() + core.area.get_area());//placement and routing overhead is 10%, core scales worse than cache 40% is accumulated from 90 to 22nm
    }
    else{
      core.area.set_area(core.area.get_area() + cores[i]->area.get_area());
      area.set_area(area.get_area() + cores[i]->area.get_area());//placement and routing overhead is 10%, core scales worse than cache 40% is accumulated from 90 to 22nm
    }
  }

  if (!XML->sys.Private_L2){
    if (numL2 >0){
      for (i = 0;i < numL2; i++){
        l2array.push_back(new SharedCache(XML,i, &interface_ip));
        if (procdynp.homoL2){
          l2.area.set_area(l2.area.get_area() + l2array[i]->area.get_area()*procdynp.numL2);
          area.set_area(area.get_area() + l2.area.get_area());//placement and routing overhead is 10%, l2 scales worse than cache 40% is accumulated from 90 to 22nm
        }
        else{
          l2.area.set_area(l2.area.get_area() + l2array[i]->area.get_area());
          area.set_area(area.get_area() + l2array[i]->area.get_area());//placement and routing overhead is 10%, l2 scales worse than cache 40% is accumulated from 90 to 22nm
        }
      }
    }
  }
  // L3
  if (numL3 >0){
    for (i = 0;i < numL3; i++){
      l3array.push_back(new SharedCache(XML,i, &interface_ip, L3));
      if (procdynp.homoL3){
        l3.area.set_area(l3.area.get_area() + l3array[i]->area.get_area()*procdynp.numL3);
        area.set_area(area.get_area() + l3.area.get_area());//placement and routing overhead is 10%, l3 scales worse than cache 40% is accumulated from 90 to 22nm
      }
      else{
        l3.area.set_area(l3.area.get_area() + l3array[i]->area.get_area());
        area.set_area(area.get_area() + l3array[i]->area.get_area());//placement and routing overhead is 10%, l3 scales worse than cache 40% is accumulated from 90 to 22nm
      }
    }
  }
  // L1Dir  
  if (numL1Dir >0){
    for (i = 0;i < numL1Dir; i++){
      l1dirarray.push_back(new SharedCache(XML,i, &interface_ip, L1Directory));
      if (procdynp.homoL1Dir){
        l1dir.area.set_area(l1dir.area.get_area() + l1dirarray[i]->area.get_area()*procdynp.numL1Dir);
        area.set_area(area.get_area() + l1dir.area.get_area());//placement and routing overhead is 10%, l1dir scales worse than cache 40% is accumulated from 90 to 22nm
      }
      else{
        l1dir.area.set_area(l1dir.area.get_area() + l1dirarray[i]->area.get_area());
        area.set_area(area.get_area() + l1dirarray[i]->area.get_area());
      }
    }
  }
  // L2Dir
  if (numL2Dir >0){
    for (i = 0;i < numL2Dir; i++)
    {
      l2dirarray.push_back(new SharedCache(XML,i, &interface_ip, L2Directory));
      if (procdynp.homoL2Dir){
        l2dir.area.set_area(l2dir.area.get_area() + l2dirarray[i]->area.get_area()*procdynp.numL2Dir);
        area.set_area(area.get_area() + l2dir.area.get_area());//placement and routing overhead is 10%, l2dir scales worse than cache 40% is accumulated from 90 to 22nm
      }
      else{
        l2dir.area.set_area(l2dir.area.get_area() + l2dirarray[i]->area.get_area());
        area.set_area(area.get_area() + l2dirarray[i]->area.get_area());
      }
    }
  }
  // memory controller
  if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0){
    mc = new MemoryController(XML, &interface_ip, MC);
    mcs.area.set_area(mcs.area.get_area()+mc->area.get_area()*XML->sys.mc.number_mcs);
    area.set_area(area.get_area()+mc->area.get_area()*XML->sys.mc.number_mcs);
  }

  //flash controller
  if (XML->sys.flashc.number_mcs >0 ){ 
    flashcontroller = new FlashController(XML, &interface_ip);
    double number_fcs = flashcontroller->fcp.num_mcs;
    flashcontrollers.area.set_area(flashcontrollers.area.get_area()+flashcontroller->area.get_area()*number_fcs);
    area.set_area(area.get_area()+flashcontrollers.area.get_area());
  }

  if (XML->sys.niu.number_units >0){
    niu = new NIUController(XML, &interface_ip);
    nius.area.set_area(nius.area.get_area()+niu->area.get_area()*XML->sys.niu.number_units);
    area.set_area(area.get_area()+niu->area.get_area()*XML->sys.niu.number_units);
  }

  if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels >0){
    pcie = new PCIeController(XML, &interface_ip);
    pcies.area.set_area(pcies.area.get_area()+pcie->area.get_area()*XML->sys.pcie.number_units);
    area.set_area(area.get_area()+pcie->area.get_area()*XML->sys.pcie.number_units);
  }

  if (numNOC >0){
    for (i = 0;i < numNOC; i++){
      if (XML->sys.NoC[i].type){
        //First add up area of routers if NoC is used
        nocs.push_back(new NoC(XML,i, &interface_ip, 1));
        if (procdynp.homoNOC){
          noc.area.set_area(noc.area.get_area() + nocs[i]->area.get_area()*procdynp.numNOC);
          area.set_area(area.get_area() + noc.area.get_area());
        }
        else{
          noc.area.set_area(noc.area.get_area() + nocs[i]->area.get_area());
          area.set_area(area.get_area() + nocs[i]->area.get_area());
        }
      }
      else{
        //Bus based interconnect
        nocs.push_back(new NoC(XML,i, &interface_ip, 1, sqrt(area.get_area()*XML->sys.NoC[i].chip_coverage)));
        if (procdynp.homoNOC){
          noc.area.set_area(noc.area.get_area() + nocs[i]->area.get_area()*procdynp.numNOC);
          area.set_area(area.get_area() + noc.area.get_area());
        }
        else{
          noc.area.set_area(noc.area.get_area() + nocs[i]->area.get_area());
          area.set_area(area.get_area() + nocs[i]->area.get_area());
        }
      }
    }

    /*
     * Compute global links associated with each NOC, if any. This must be done at the end (even after the NOC router part) since the total chip
     * area must be obtain to decide the link routing
     */
    for (i = 0;i < numNOC; i++){
      if (nocs[i]->nocdynp.has_global_link && XML->sys.NoC[i].type){
        nocs[i]->init_link_bus(sqrt(area.get_area()*XML->sys.NoC[i].chip_coverage));//compute global links
        if (procdynp.homoNOC){
          noc.area.set_area(noc.area.get_area() + nocs[i]->link_bus_tot_per_Router.area.get_area()
              * nocs[i]->nocdynp.total_nodes
              * procdynp.numNOC);
          area.set_area(area.get_area() + nocs[i]->link_bus_tot_per_Router.area.get_area()
              * nocs[i]->nocdynp.total_nodes
              * procdynp.numNOC);
        }
        else{
          noc.area.set_area(noc.area.get_area() + nocs[i]->link_bus_tot_per_Router.area.get_area()
              * nocs[i]->nocdynp.total_nodes);
          area.set_area(area.get_area() + nocs[i]->link_bus_tot_per_Router.area.get_area()
              * nocs[i]->nocdynp.total_nodes);
        }
      }
    }
  }
}

void Processor::compute(ParseXML *fresh_XML){
  // if a new XML is received, reset all stats for a new round of power computation
  if(fresh_XML != nullptr){
    refresh_param(fresh_XML);
    clear_power();
  }

  /** Power Computation of Custom Block **/
  // Following are just example usage of given statistics
  if(XML->sys.number_of_custom_blocks > 0){
    CIM_SRAM.computePower_Frequency(XML->sys.CIM_SRAM.frequency, XML->sys.CIM_SRAM.activation_factor);
  }

  int i;
  double pppm_t[4]    = {1,1,1,1};
  for (i = 0;i < numCore; i++)
  {
      cores[i]->computeEnergy();
      cores[i]->computeEnergy(false);
      if (procdynp.homoCore){        
        set_pppm(pppm_t,cores[i]->clockRate*procdynp.numCore, procdynp.numCore,procdynp.numCore,procdynp.numCore);
        core.power = core.power + cores[i]->power*pppm_t;
        set_pppm(pppm_t,1/cores[i]->executionTime, procdynp.numCore,procdynp.numCore,procdynp.numCore);
        core.rt_power = core.rt_power + cores[i]->rt_power*pppm_t;
        power = power + core.power;
        rt_power = rt_power + core.rt_power;
      }
      else{
        set_pppm(pppm_t,cores[i]->clockRate, 1, 1, 1);
        core.power = core.power + cores[i]->power*pppm_t;
        power = power  + cores[i]->power*pppm_t;

        set_pppm(pppm_t,1/cores[i]->executionTime, 1, 1, 1);
        core.rt_power = core.rt_power + cores[i]->rt_power*pppm_t;
        rt_power = rt_power  + cores[i]->rt_power*pppm_t;
      }
  }

  if (!XML->sys.Private_L2)
  {
  if (numL2 >0)
    for (i = 0;i < numL2; i++)
    {
      l2array[i]->computeEnergy();
      l2array[i]->computeEnergy(false);
      if (procdynp.homoL2){
        set_pppm(pppm_t,l2array[i]->cachep.clockRate*procdynp.numL2, procdynp.numL2,procdynp.numL2,procdynp.numL2);
        l2.power = l2.power + l2array[i]->power*pppm_t;
        set_pppm(pppm_t,1/l2array[i]->cachep.executionTime, procdynp.numL2,procdynp.numL2,procdynp.numL2);
        l2.rt_power = l2.rt_power + l2array[i]->rt_power*pppm_t;
        power = power  + l2.power;
        rt_power = rt_power  + l2.rt_power;
      }
      else{
        set_pppm(pppm_t,l2array[i]->cachep.clockRate, 1, 1, 1);
        l2.power = l2.power + l2array[i]->power*pppm_t;
        power = power  + l2array[i]->power*pppm_t;;
        set_pppm(pppm_t,1/l2array[i]->cachep.executionTime, 1, 1, 1);
        l2.rt_power = l2.rt_power + l2array[i]->rt_power*pppm_t;
        rt_power = rt_power  + l2array[i]->rt_power*pppm_t;
      }
    }
  }

  if (numL3 >0)
    for (i = 0;i < numL3; i++)
    {
      l3array[i]->computeEnergy();
      l3array[i]->computeEnergy(false);
      if (procdynp.homoL3){
        set_pppm(pppm_t,l3array[i]->cachep.clockRate*procdynp.numL3, procdynp.numL3,procdynp.numL3,procdynp.numL3);
        l3.power = l3.power + l3array[i]->power*pppm_t;
        set_pppm(pppm_t,1/l3array[i]->cachep.executionTime, procdynp.numL3,procdynp.numL3,procdynp.numL3);
        l3.rt_power = l3.rt_power + l3array[i]->rt_power*pppm_t;
        power = power  + l3.power;
        rt_power = rt_power  + l3.rt_power;
      }
      else{
        set_pppm(pppm_t,l3array[i]->cachep.clockRate, 1, 1, 1);
        l3.power = l3.power + l3array[i]->power*pppm_t;
        power = power  + l3array[i]->power*pppm_t;
        set_pppm(pppm_t,1/l3array[i]->cachep.executionTime, 1, 1, 1);
        l3.rt_power = l3.rt_power + l3array[i]->rt_power*pppm_t;
        rt_power = rt_power  + l3array[i]->rt_power*pppm_t;
      }
    }
  if (numL1Dir >0)
    for (i = 0;i < numL1Dir; i++)
    {
      l1dirarray[i]->computeEnergy();
      l1dirarray[i]->computeEnergy(false);
      if (procdynp.homoL1Dir){
        set_pppm(pppm_t,l1dirarray[i]->cachep.clockRate*procdynp.numL1Dir, procdynp.numL1Dir,procdynp.numL1Dir,procdynp.numL1Dir);
        l1dir.power = l1dir.power + l1dirarray[i]->power*pppm_t;
        set_pppm(pppm_t,1/l1dirarray[i]->cachep.executionTime, procdynp.numL1Dir,procdynp.numL1Dir,procdynp.numL1Dir);
        l1dir.rt_power = l1dir.rt_power + l1dirarray[i]->rt_power*pppm_t;
        power = power  + l1dir.power;
        rt_power = rt_power  + l1dir.rt_power;
      }
      else{
        set_pppm(pppm_t,l1dirarray[i]->cachep.clockRate, 1, 1, 1);
        l1dir.power = l1dir.power + l1dirarray[i]->power*pppm_t;
        power = power  + l1dirarray[i]->power;
        set_pppm(pppm_t,1/l1dirarray[i]->cachep.executionTime, 1, 1, 1);
        l1dir.rt_power = l1dir.rt_power + l1dirarray[i]->rt_power*pppm_t;
        rt_power = rt_power  + l1dirarray[i]->rt_power;
      }
    }

  if (numL2Dir >0)
    for (i = 0;i < numL2Dir; i++)
    {
      l2dirarray[i]->computeEnergy();
      l2dirarray[i]->computeEnergy(false);
      if (procdynp.homoL2Dir){
        set_pppm(pppm_t,l2dirarray[i]->cachep.clockRate*procdynp.numL2Dir, procdynp.numL2Dir,procdynp.numL2Dir,procdynp.numL2Dir);
        l2dir.power = l2dir.power + l2dirarray[i]->power*pppm_t;
        set_pppm(pppm_t,1/l2dirarray[i]->cachep.executionTime, procdynp.numL2Dir,procdynp.numL2Dir,procdynp.numL2Dir);
        l2dir.rt_power = l2dir.rt_power + l2dirarray[i]->rt_power*pppm_t;
        power = power  + l2dir.power;
        rt_power = rt_power  + l2dir.rt_power;

      }
      else{
        set_pppm(pppm_t,l2dirarray[i]->cachep.clockRate, 1, 1, 1);
        l2dir.power = l2dir.power + l2dirarray[i]->power*pppm_t;
        power = power  + l2dirarray[i]->power*pppm_t;
        set_pppm(pppm_t,1/l2dirarray[i]->cachep.executionTime, 1, 1, 1);
        l2dir.rt_power = l2dir.rt_power + l2dirarray[i]->rt_power*pppm_t;
        rt_power = rt_power  + l2dirarray[i]->rt_power*pppm_t;
      }
    }

  if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0)
  {
    mc->computeEnergy();
    mc->computeEnergy(false);
    set_pppm(pppm_t,XML->sys.mc.number_mcs*mc->mcp.clockRate, XML->sys.mc.number_mcs,XML->sys.mc.number_mcs,XML->sys.mc.number_mcs);
    mcs.power = mc->power*pppm_t;
    power = power  + mcs.power;
    set_pppm(pppm_t,1/mc->mcp.executionTime, XML->sys.mc.number_mcs,XML->sys.mc.number_mcs,XML->sys.mc.number_mcs);
    mcs.rt_power = mc->rt_power*pppm_t;
    rt_power = rt_power  + mcs.rt_power;
  }

  if (XML->sys.flashc.number_mcs >0 )//flash controller
  {
    flashcontroller->computeEnergy();
    flashcontroller->computeEnergy(false);
    double number_fcs = flashcontroller->fcp.num_mcs;
    set_pppm(pppm_t,number_fcs, number_fcs ,number_fcs, number_fcs );
    flashcontrollers.power = flashcontroller->power*pppm_t;
    power = power  + flashcontrollers.power;
    set_pppm(pppm_t,number_fcs , number_fcs ,number_fcs ,number_fcs );
    flashcontrollers.rt_power = flashcontroller->rt_power*pppm_t;
    rt_power = rt_power  + flashcontrollers.rt_power;
  }

  if (XML->sys.niu.number_units >0)
  {
    niu->computeEnergy();
    niu->computeEnergy(false);
    set_pppm(pppm_t,XML->sys.niu.number_units*niu->niup.clockRate, XML->sys.niu.number_units,XML->sys.niu.number_units,XML->sys.niu.number_units);
    nius.power = niu->power*pppm_t;
    power = power  + nius.power;
    set_pppm(pppm_t,XML->sys.niu.number_units*niu->niup.clockRate, XML->sys.niu.number_units,XML->sys.niu.number_units,XML->sys.niu.number_units);
    nius.rt_power = niu->rt_power*pppm_t;
    rt_power = rt_power  + nius.rt_power;
  }

  if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels >0)
  {
    pcie->computeEnergy();
    pcie->computeEnergy(false);
    set_pppm(pppm_t,XML->sys.pcie.number_units*pcie->pciep.clockRate, XML->sys.pcie.number_units,XML->sys.pcie.number_units,XML->sys.pcie.number_units);
    pcies.power = pcie->power*pppm_t;
    power = power  + pcies.power;
    set_pppm(pppm_t,XML->sys.pcie.number_units*pcie->pciep.clockRate, XML->sys.pcie.number_units,XML->sys.pcie.number_units,XML->sys.pcie.number_units);
    pcies.rt_power = pcie->rt_power*pppm_t;
    rt_power = rt_power  + pcies.rt_power;
  }


  //Compute energy of NoC (w or w/o links) or buses
  for (i = 0;i < numNOC; i++){
    nocs[i]->computeEnergy();
    nocs[i]->computeEnergy(false);
    if (procdynp.homoNOC){
      set_pppm(pppm_t,procdynp.numNOC*nocs[i]->nocdynp.clockRate, procdynp.numNOC,procdynp.numNOC,procdynp.numNOC);
      noc.power = noc.power + nocs[i]->power*pppm_t;
      set_pppm(pppm_t,1/nocs[i]->nocdynp.executionTime, procdynp.numNOC,procdynp.numNOC,procdynp.numNOC);
      noc.rt_power = noc.rt_power + nocs[i]->rt_power*pppm_t;
      power = power  + noc.power;
      rt_power = rt_power  + noc.rt_power;
    }
    else{
      set_pppm(pppm_t,nocs[i]->nocdynp.clockRate, 1, 1, 1);
      noc.power = noc.power + nocs[i]->power*pppm_t;
      power = power  + nocs[i]->power*pppm_t;
      set_pppm(pppm_t,1/nocs[i]->nocdynp.executionTime, 1, 1, 1);
      noc.rt_power = noc.rt_power + nocs[i]->rt_power*pppm_t;
      rt_power = rt_power  + nocs[i]->rt_power*pppm_t;
    }
  }
}

void Processor::displayDeviceType(int device_type_, uint32_t indent)
{
  string indent_str(indent, ' ');

  switch ( device_type_ ) {

    case 0 :
      cout <<indent_str<<"Device Type= "<<"ITRS high performance device type"<<endl;
      break;
    case 1 :
      cout <<indent_str<<"Device Type= "<<"ITRS low standby power device type"<<endl;
      break;
    case 2 :
      cout <<indent_str<<"Device Type= "<<"ITRS low operating power device type"<<endl;
      break;
    case 3 :
      cout <<indent_str<<"Device Type= "<<"LP-DRAM device type"<<endl;
      break;
    case 4 :
      cout <<indent_str<<"Device Type= "<<"COMM-DRAM device type"<<endl;
      break;
    default :
      {
        cout <<indent_str<<"Unknown Device Type"<<endl;
        exit(0);
      }
  }
}

void Processor::displayInterconnectType(int interconnect_type_, uint32_t indent)
{
  string indent_str(indent, ' ');

  switch ( interconnect_type_ ) {

    case 0 :
      cout <<indent_str<<"Interconnect metal projection= "<<"aggressive interconnect technology projection"<<endl;
      break;
    case 1 :
      cout <<indent_str<<"Interconnect metal projection= "<<"conservative interconnect technology projection"<<endl;
      break;
    default :
      {
        cout <<indent_str<<"Unknown Interconnect Projection Type"<<endl;
        exit(0);
      }
  }
}

void Processor::displayEnergy(uint32_t indent, int plevel, bool is_tdp)
{
#ifndef ORIGINAL_OUTPUT
int i;
bool long_channel = XML->sys.longer_channel_device;
bool power_gating = XML->sys.power_gating;
string indent_str(indent, ' ');
string indent_str_next(indent+2, ' ');
if (is_tdp)
{

  if (plevel<5)
  {
    cout<<"\nMcPAT (version "<< VER_MAJOR <<"."<< VER_MINOR
        << " of " << VER_UPDATE << ") results (current print level is "<< plevel
    <<", please increase print level to see the details in components): "<<endl;
  }
  else
  {
    cout<<"\nMcPAT (version "<< VER_MAJOR <<"."<< VER_MINOR
              << " of " << VER_UPDATE << ") results  (current print level is 5)"<< endl;
  }
  cout <<"*****************************************************************************************"<<endl;
  cout <<indent_str<<"Technology "<<XML->sys.core_tech_node<<" nm"<<endl;
  //cout <<indent_str<<"Device Type= "<<XML->sys.device_type<<endl;
  if (long_channel)
    cout <<indent_str<<"Using Long Channel Devices When Appropriate"<<endl;
  //cout <<indent_str<<"Interconnect metal projection= "<<XML->sys.interconnect_projection_type<<endl;
  displayInterconnectType(XML->sys.interconnect_projection_type, indent);
  cout <<indent_str<<"Core clock Rate(MHz) "<<XML->sys.core[0].clock_rate<<endl;
    cout <<endl;
  cout <<"*****************************************************************************************"<<endl;
  if (plevel >1)
  {
    if(procdynp.homoCore){
      for (i = 0;i < procdynp.numCore; i++){
        cores[0]->displayEnergy(indent+4,plevel,is_tdp);
      }
    }else{
      for (i = 0;i < numCore; i++){
        cores[i]->displayEnergy(indent+4,plevel,is_tdp);
      }
    }

    if (!XML->sys.Private_L2){			
      if(procdynp.homoL2){
        for (i = 0;i < procdynp.numL2; i++){
          l2array[0]->displayEnergy(indent+4,is_tdp);
        }
      }else{
        for (i = 0;i < numL2; i++){
          l2array[i]->displayEnergy(indent+4,is_tdp);
        }
      }
    }
    if(procdynp.homoL3){
      for (i = 0;i < procdynp.numL3; i++){
        l3array[0]->displayEnergy(indent+4,is_tdp);
      }
    }else{
      for (i = 0;i < numL3; i++){
        l3array[i]->displayEnergy(indent+4,is_tdp);
      }
    }
    if(procdynp.homoL1Dir){
      for (i = 0;i < procdynp.numL1Dir; i++){
        l1dirarray[0]->displayEnergy(indent+4,is_tdp);
      }
    }else{
      for (i = 0;i < numL1Dir; i++){
        l1dirarray[i]->displayEnergy(indent+4,is_tdp);
      }
    }
    if(procdynp.homoL2Dir){
      for (i = 0;i < procdynp.numL2Dir; i++){
        l2dirarray[0]->displayEnergy(indent+4,is_tdp);
      }
    }else{
      for (i = 0;i < numL2Dir; i++){
        l2dirarray[i]->displayEnergy(indent+4,is_tdp);
      }
    }
    if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0)
    {
      mc->displayEnergy(indent+4,is_tdp);
    }
    if (XML->sys.flashc.number_mcs >0 && XML->sys.flashc.memory_channels_per_mc>0)
    {
      flashcontroller->displayEnergy(indent+4,is_tdp);
    }
    if (XML->sys.niu.number_units >0 )
    {
      niu->displayEnergy(indent+4,is_tdp);
    }
    if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels>0)
    {
      pcie->displayEnergy(indent+4,is_tdp);
    }
    if(procdynp.homoNOC){
      for (i = 0;i < procdynp.numNOC; i++){
        nocs[0]->displayEnergy(indent+4,plevel,is_tdp);
      }
    }else{
      for (i = 0;i < numNOC; i++){
        nocs[i]->displayEnergy(indent+4,plevel,is_tdp);
      }
    }
    CIM_SRAM.displayPower();
  }
}
#else
  int i;
  bool long_channel = XML->sys.longer_channel_device;
  bool power_gating = XML->sys.power_gating;
  string indent_str(indent, ' ');
  string indent_str_next(indent+2, ' ');
  if (is_tdp)
  {

    if (plevel<5)
    {
      cout<<"\nMcPAT (version "<< VER_MAJOR <<"."<< VER_MINOR
          << " of " << VER_UPDATE << ") results (current print level is "<< plevel
      <<", please increase print level to see the details in components): "<<endl;
    }
    else
    {
      cout<<"\nMcPAT (version "<< VER_MAJOR <<"."<< VER_MINOR
                << " of " << VER_UPDATE << ") results  (current print level is 5)"<< endl;
    }
    cout <<"*****************************************************************************************"<<endl;
    cout <<indent_str<<"Technology "<<XML->sys.core_tech_node<<" nm"<<endl;
    //cout <<indent_str<<"Device Type= "<<XML->sys.device_type<<endl;
    if (long_channel)
      cout <<indent_str<<"Using Long Channel Devices When Appropriate"<<endl;
    //cout <<indent_str<<"Interconnect metal projection= "<<XML->sys.interconnect_projection_type<<endl;
    displayInterconnectType(XML->sys.interconnect_projection_type, indent);
    cout <<indent_str<<"Core clock Rate(MHz) "<<XML->sys.core[0].clock_rate<<endl;
      cout <<endl;
    cout <<"*****************************************************************************************"<<endl;
    cout <<"Processor: "<<endl;
    cout << indent_str << "Area = " << area.get_area()*1e-6<< " mm^2" << endl;
    cout << indent_str << "Peak Power = " << power.readOp.dynamic +
      (long_channel? power.readOp.longer_channel_leakage:power.readOp.leakage) + power.readOp.gate_leakage <<" W" << endl;
    cout << indent_str << "Total Leakage = " <<
      (long_channel? power.readOp.longer_channel_leakage:power.readOp.leakage) + power.readOp.gate_leakage <<" W" << endl;
    cout << indent_str << "Peak Dynamic = " << power.readOp.dynamic << " W" << endl;
    cout << indent_str << "Subthreshold Leakage = " << (long_channel? power.readOp.longer_channel_leakage:power.readOp.leakage) <<" W" << endl;
    if (power_gating) cout << indent_str << "Subthreshold Leakage with power gating = "
        << (long_channel? power.readOp.power_gated_with_long_channel_leakage : power.readOp.power_gated_leakage)  << " W" << endl;
    cout << indent_str << "Gate Leakage = " << power.readOp.gate_leakage << " W" << endl;
    cout << indent_str << "Runtime Dynamic = " << rt_power.readOp.dynamic << " W" << endl;
    cout <<endl;
    if (numCore >0){
    cout <<indent_str<<"Total Cores: "<<XML->sys.number_of_cores << " cores "<<endl;
    displayDeviceType(XML->sys.device_type,indent);
    cout << indent_str_next << "Area = " << core.area.get_area()*1e-6<< " mm^2" << endl;
    cout << indent_str_next << "Peak Dynamic = " << core.power.readOp.dynamic << " W" << endl;
    cout << indent_str_next << "Subthreshold Leakage = "
      << (long_channel? core.power.readOp.longer_channel_leakage:core.power.readOp.leakage) <<" W" << endl;
    if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
        << (long_channel? core.power.readOp.power_gated_with_long_channel_leakage : core.power.readOp.power_gated_leakage)  << " W" << endl;
    cout << indent_str_next << "Gate Leakage = " << core.power.readOp.gate_leakage << " W" << endl;
    cout << indent_str_next << "Runtime Dynamic = " << core.rt_power.readOp.dynamic << " W" << endl;
    cout <<endl;
    }
    if (!XML->sys.Private_L2)
    {
      if (numL2 >0){
        cout <<indent_str<<"Total L2s: "<<endl;
        displayDeviceType(XML->sys.L2[0].device_type,indent);
        cout << indent_str_next << "Area = " << l2.area.get_area()*1e-6<< " mm^2" << endl;
        cout << indent_str_next << "Peak Dynamic = " << l2.power.readOp.dynamic << " W" << endl;
        cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? l2.power.readOp.longer_channel_leakage:l2.power.readOp.leakage) <<" W" << endl;
        if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
            << (long_channel? l2.power.readOp.power_gated_with_long_channel_leakage : l2.power.readOp.power_gated_leakage)  << " W" << endl;
        cout << indent_str_next << "Gate Leakage = " << l2.power.readOp.gate_leakage << " W" << endl;
        cout << indent_str_next << "Runtime Dynamic = " << l2.rt_power.readOp.dynamic << " W" << endl;
        cout <<endl;
      }
    }
    if (numL3 >0){
      cout <<indent_str<<"Total L3s: "<<endl;
      displayDeviceType(XML->sys.L3[0].device_type, indent);
      cout << indent_str_next << "Area = " << l3.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << l3.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? l3.power.readOp.longer_channel_leakage:l3.power.readOp.leakage) <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? l3.power.readOp.power_gated_with_long_channel_leakage : l3.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << l3.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << l3.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (numL1Dir >0){
      cout <<indent_str<<"Total First Level Directory: "<<endl;
      displayDeviceType(XML->sys.L1Directory[0].device_type, indent);
      cout << indent_str_next << "Area = " << l1dir.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << l1dir.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? l1dir.power.readOp.longer_channel_leakage:l1dir.power.readOp.leakage) <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? l1dir.power.readOp.power_gated_with_long_channel_leakage : l1dir.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << l1dir.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << l1dir.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (numL2Dir >0){
      cout <<indent_str<<"Total Second Level Directory: "<<endl;
      displayDeviceType(XML->sys.L1Directory[0].device_type, indent);
      cout << indent_str_next << "Area = " << l2dir.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << l2dir.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? l2dir.power.readOp.longer_channel_leakage:l2dir.power.readOp.leakage) <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? l2dir.power.readOp.power_gated_with_long_channel_leakage : l2dir.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << l2dir.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << l2dir.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (numNOC >0){
      cout <<indent_str<<"Total NoCs (Network/Bus): "<<endl;
      displayDeviceType(XML->sys.device_type, indent);
      cout << indent_str_next << "Area = " << noc.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << noc.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? noc.power.readOp.longer_channel_leakage:noc.power.readOp.leakage) <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? noc.power.readOp.power_gated_with_long_channel_leakage : noc.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << noc.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << noc.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0)
    {
      cout <<indent_str<<"Total MCs: "<<XML->sys.mc.number_mcs << " Memory Controllers "<<endl;
      displayDeviceType(XML->sys.device_type, indent);
      cout << indent_str_next << "Area = " << mcs.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << mcs.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? mcs.power.readOp.longer_channel_leakage:mcs.power.readOp.leakage)  <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? mcs.power.readOp.power_gated_with_long_channel_leakage : mcs.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << mcs.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << mcs.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (XML->sys.flashc.number_mcs >0)
    {
      cout <<indent_str<<"Total Flash/SSD Controllers: "<<flashcontroller->fcp.num_mcs << " Flash/SSD Controllers "<<endl;
      displayDeviceType(XML->sys.device_type, indent);
      cout << indent_str_next << "Area = " << flashcontrollers.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << flashcontrollers.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? flashcontrollers.power.readOp.longer_channel_leakage:flashcontrollers.power.readOp.leakage)  <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? flashcontrollers.power.readOp.power_gated_with_long_channel_leakage : flashcontrollers.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << flashcontrollers.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << flashcontrollers.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (XML->sys.niu.number_units >0 )
    {
      cout <<indent_str<<"Total NIUs: "<<niu->niup.num_units << " Network Interface Units "<<endl;
      displayDeviceType(XML->sys.device_type, indent);
      cout << indent_str_next << "Area = " << nius.area.get_area()*1e-6<< " mm^2" << endl;
      cout << indent_str_next << "Peak Dynamic = " << nius.power.readOp.dynamic << " W" << endl;
      cout << indent_str_next << "Subthreshold Leakage = "
        << (long_channel? nius.power.readOp.longer_channel_leakage:nius.power.readOp.leakage)  <<" W" << endl;
      if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
          << (long_channel? nius.power.readOp.power_gated_with_long_channel_leakage : nius.power.readOp.power_gated_leakage)  << " W" << endl;
      cout << indent_str_next << "Gate Leakage = " << nius.power.readOp.gate_leakage << " W" << endl;
      cout << indent_str_next << "Runtime Dynamic = " << nius.rt_power.readOp.dynamic << " W" << endl;
      cout <<endl;
    }
    if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels>0)
        {
          cout <<indent_str<<"Total PCIes: "<<pcie->pciep.num_units << " PCIe Controllers "<<endl;
          displayDeviceType(XML->sys.device_type, indent);
          cout << indent_str_next << "Area = " << pcies.area.get_area()*1e-6<< " mm^2" << endl;
          cout << indent_str_next << "Peak Dynamic = " << pcies.power.readOp.dynamic << " W" << endl;
          cout << indent_str_next << "Subthreshold Leakage = "
            << (long_channel? pcies.power.readOp.longer_channel_leakage:pcies.power.readOp.leakage)  <<" W" << endl;
          if (power_gating) cout << indent_str_next << "Subthreshold Leakage with power gating = "
              << (long_channel? pcies.power.readOp.power_gated_with_long_channel_leakage : pcies.power.readOp.power_gated_leakage)  << " W" << endl;
          cout << indent_str_next << "Gate Leakage = " << pcies.power.readOp.gate_leakage << " W" << endl;
          cout << indent_str_next << "Runtime Dynamic = " << pcies.rt_power.readOp.dynamic << " W" << endl;
          cout <<endl;
        }
    cout <<"*****************************************************************************************"<<endl;
    if (plevel >1)
    {
      for (i = 0;i < numCore; i++)
      {
        cores[i]->displayEnergy(indent+4,plevel,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      if (!XML->sys.Private_L2)
      {
        for (i = 0;i < numL2; i++)
        {
          l2array[i]->displayEnergy(indent+4,is_tdp);
          cout <<"*****************************************************************************************"<<endl;
        }
      }
      for (i = 0;i < numL3; i++)
      {
        l3array[i]->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      for (i = 0;i < numL1Dir; i++)
      {
        l1dirarray[i]->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      for (i = 0;i < numL2Dir; i++)
      {
        l2dirarray[i]->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0)
      {
        mc->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      if (XML->sys.flashc.number_mcs >0 && XML->sys.flashc.memory_channels_per_mc>0)
      {
        flashcontroller->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      if (XML->sys.niu.number_units >0 )
      {
        niu->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
      if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels>0)
      {
        pcie->displayEnergy(indent+4,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }

      for (i = 0;i < numNOC; i++)
      {
        nocs[i]->displayEnergy(indent+4,plevel,is_tdp);
        cout <<"*****************************************************************************************"<<endl;
      }
    }
  }
  else
  {

  }
#endif
}

void Processor::set_proc_param()
{	
  bool debug = false;
  procdynp.homoCore = bool(debug?1:XML->sys.homogeneous_cores);
  procdynp.homoL2   = bool(debug?1:XML->sys.homogeneous_L2s);
  procdynp.homoL3   = bool(debug?1:XML->sys.homogeneous_L3s);
  procdynp.homoNOC  = bool(debug?1:XML->sys.homogeneous_NoCs);
  procdynp.homoL1Dir  = bool(debug?1:XML->sys.homogeneous_L1Directories);
  procdynp.homoL2Dir  = bool(debug?1:XML->sys.homogeneous_L2Directories);

  procdynp.numCore = XML->sys.number_of_cores;
  procdynp.numL2   = XML->sys.number_of_L2s;
  procdynp.numL3   = XML->sys.number_of_L3s;
  procdynp.numNOC  = XML->sys.number_of_NoCs;
  procdynp.numL1Dir  = XML->sys.number_of_L1Directories;
  procdynp.numL2Dir  = XML->sys.number_of_L2Directories;
  procdynp.numMC = XML->sys.mc.number_mcs;
  procdynp.numMCChannel = XML->sys.mc.memory_channels_per_mc;

  /* Basic parameters*/
  interface_ip.data_arr_ram_cell_tech_type    = debug?0:XML->sys.device_type;
  interface_ip.data_arr_peri_global_tech_type = debug?0:XML->sys.device_type;
  interface_ip.tag_arr_ram_cell_tech_type     = debug?0:XML->sys.device_type;
  interface_ip.tag_arr_peri_global_tech_type  = debug?0:XML->sys.device_type;

  interface_ip.specific_hp_vdd = false;
  interface_ip.specific_lop_vdd = false;
  interface_ip.specific_lstp_vdd = false;

  interface_ip.specific_vcc_min = false;

  interface_ip.ic_proj_type     = debug?0:XML->sys.interconnect_projection_type;
  interface_ip.delay_wt                = 100;//Fixed number, make sure timing can be satisfied.
  interface_ip.area_wt                 = 0;//Fixed number, This is used to exhaustive search for individual components.
  interface_ip.dynamic_power_wt        = 100;//Fixed number, This is used to exhaustive search for individual components.
  interface_ip.leakage_power_wt        = 0;
  interface_ip.cycle_time_wt           = 0;

  interface_ip.delay_dev                = 10000;//Fixed number, make sure timing can be satisfied.
  interface_ip.area_dev                 = 10000;//Fixed number, This is used to exhaustive search for individual components.
  interface_ip.dynamic_power_dev        = 10000;//Fixed number, This is used to exhaustive search for individual components.
  interface_ip.leakage_power_dev        = 10000;
  interface_ip.cycle_time_dev           = 10000;

  interface_ip.ed                       = 2;
  interface_ip.burst_len      = 1;//parameters are fixed for processor section, since memory is processed separately
  interface_ip.int_prefetch_w = 1;
  interface_ip.page_sz_bits   = 0;
  interface_ip.temp = debug?360: XML->sys.temperature;
  interface_ip.F_sz_nm         = debug?90:XML->sys.core_tech_node;//XML->sys.core_tech_node;
  interface_ip.F_sz_um         = interface_ip.F_sz_nm / 1000;

  //***********This section of code does not have real meaning, they are just to ensure all data will have initial value to prevent errors.
  //They will be overridden  during each components initialization
  interface_ip.cache_sz            =64;
  interface_ip.line_sz             = 1;
  interface_ip.assoc               = 1;
  interface_ip.nbanks              = 1;
  interface_ip.out_w               = interface_ip.line_sz*8;
  interface_ip.specific_tag        = 1;
  interface_ip.tag_w               = 64;
  interface_ip.access_mode         = 2;

  interface_ip.obj_func_dyn_energy = 0;
  interface_ip.obj_func_dyn_power  = 0;
  interface_ip.obj_func_leak_power = 0;
  interface_ip.obj_func_cycle_t    = 1;

  interface_ip.is_main_mem     = false;
  interface_ip.rpters_in_htree = true ;
  interface_ip.ver_htree_wires_over_array = 0;
  interface_ip.broadcast_addr_din_over_ver_htrees = 0;

  interface_ip.num_rw_ports        = 1;
  interface_ip.num_rd_ports        = 0;
  interface_ip.num_wr_ports        = 0;
  interface_ip.num_se_rd_ports     = 0;
  interface_ip.num_search_ports    = 1;
  interface_ip.nuca                = 0;
  interface_ip.nuca_bank_count     = 0;
  interface_ip.is_cache            =true;
  interface_ip.pure_ram            =false;
  interface_ip.pure_cam            =false;
  interface_ip.force_cache_config  =false;
  interface_ip.power_gating  		 =XML->sys.power_gating;

  if (XML->sys.Embedded)
  {
    interface_ip.wt                  =Global_30;
    interface_ip.wire_is_mat_type = 0;
    interface_ip.wire_os_mat_type = 0;
  }
  else  
  {
    interface_ip.wt                  =Global;
    interface_ip.wire_is_mat_type = 2;
    interface_ip.wire_os_mat_type = 2;
  }
  interface_ip.force_wiretype      = false;
  interface_ip.print_detail        = 1;
  interface_ip.add_ecc_b_          =true;
}


void Processor::refresh_param(ParseXML *fresh_XML){
  /**
   * There're two things to be refreshed:
   * 1. XML struct used accross nearly all components.
   *    ---- The XML is sometimes used by energy computing function.
   * 2. set_XXX_param()
   *    ---- This configures some values inside each component, which 
   *         are also used in energy computing.
   * 
   * Several questions you may asked:
   * 1. Can we do set_XXX_param() indicvidually as shown below?
   *    The answer is yes. 
   *    Though set_XXX_param is originally done before optimization, you can easily check that 
   *    optimization makes no change upon the params & stats in set_XXX_param, since they operate upon different hierachy
   *    of components. Thus, resetting those parameters after optimization should also work.
   * 2. Does refreshing XML and resetting params cover all the stats that needs to be refreshed?
   *    The answer is yes. 
   *    You can check it by looking through the stats in XML_Parse.h. Search them in the whole project, and you'll find 
   *    that all stats related to energy computation is covered by XML and set_XXX_param(). 
   */
  
  int i;

  XML = fresh_XML;
  // set_proc_param(); // I comment this because it has nothing to do with power. I've checked.
  for (i = 0;i < numCore; i++){
    cores[i]->XML = fresh_XML;
    cores[i]->ifu->XML = fresh_XML;
    cores[i]->lsu->XML = fresh_XML;
    cores[i]->mmu->XML = fresh_XML;
    cores[i]->exu->XML = fresh_XML;
    cores[i]->rnu->XML = fresh_XML;
    cores[i]->undiffCore->XML = fresh_XML;
    cores[i]->set_core_param();
    if (XML->sys.Private_L2) {
      cores[i]->l2cache->XML = fresh_XML;
      cores[i]->l2cache->set_cache_param();
    } 
  }
  // return;

  if (!XML->sys.Private_L2){
    for (i = 0;i < numL2; i++){
      l2array[i]->XML = fresh_XML;
      l2array[i]->set_cache_param();
    }
  }

  for (i = 0;i < numL3; i++){
    l3array[i]->XML = fresh_XML;
    l3array[i]->set_cache_param();
  }

  for (i = 0;i < numL1Dir; i++){
    l1dirarray[i]->XML = fresh_XML;
    l1dirarray[i]->set_cache_param();
  }

  for (i = 0;i < numL2Dir; i++){
    l2dirarray[i]->XML = fresh_XML;
    l2dirarray[i]->set_cache_param();
  }

  if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0){
    mc->XML = fresh_XML;
    mc->frontend->XML = fresh_XML;
    mc->set_mc_param();
  }

  if (XML->sys.flashc.number_mcs >0 ){
    flashcontroller->XML = fresh_XML; 
    flashcontroller->set_fc_param();
  }

  if (XML->sys.niu.number_units >0){
    niu->XML = fresh_XML;
    niu->set_niu_param();
  }

  if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels >0){
    pcie->XML = fresh_XML;
    pcie->set_pcie_param();
  }

  for (i = 0;i < numNOC; i++){
    nocs[i]->XML = fresh_XML;
    nocs[i]->set_noc_param();
    // The below line seems to be only related to area. So I comment it temporarily.
    // if (nocs[i]->nocdynp.has_global_link && XML->sys.NoC[i].type){
    //   nocs[i]->init_link_bus(sqrt(area.get_area()*XML->sys.NoC[i].chip_coverage));//compute global links
    // }
  }
}


Processor::~Processor(){
  while (!cores.empty())
  {
    delete cores.back();
    cores.pop_back();
  }
  while (!l2array.empty())
  {
    delete l2array.back();
    l2array.pop_back();
  }
  while (!l3array.empty())
  {
    delete l3array.back();
    l3array.pop_back();
  }
  while (!nocs.empty())
  {
    delete nocs.back();
    nocs.pop_back();
  }
  while (!l1dirarray.empty())
  {
    delete l1dirarray.back();
    l1dirarray.pop_back();
  }
  while (!l2dirarray.empty())
  {
    delete l2dirarray.back();
    l2dirarray.pop_back();
  }
  if (mc)
  {
    delete mc;
    mc=0;
  }
  if (niu)
  {
    delete niu;
    niu =0;
  }
  if (pcie)
  {
    delete pcie;
    pcie=0;
  }
  if (flashcontroller)
  {
    delete flashcontroller;
    flashcontroller = 0;
  }
};  

void Processor::clear_power(){
  int i;
  power.reset();
  rt_power.reset();
  core.power.reset();
  core.rt_power.reset();
  for (i = 0;i < numCore; i++){
      // reset power for core
      cores[i]->power.reset();
      cores[i]->rt_power.reset();
      // reset power for components in core
      cores[i]->ifu->power.reset();
      cores[i]->ifu->rt_power.reset();
      // cores[i]->ifu->icache.power.reset();
      // cores[i]->ifu->icache.rt_power.reset();
      // cores[i]->ifu->icache.power_t.reset();
      // cores[i]->ifu->IB->power.reset();
      // cores[i]->ifu->IB->rt_power.reset();
      // cores[i]->ifu->IB->power_t.reset();
      // cores[i]->ifu->ID_inst->power.reset();
      // cores[i]->ifu->ID_inst->rt_power.reset();
      // cores[i]->ifu->ID_inst->power_t.reset();
      // cores[i]->ifu->ID_operand->power.reset();
      // cores[i]->ifu->ID_operand->rt_power.reset();
      // cores[i]->ifu->ID_operand->power_t.reset();
      // cores[i]->ifu->ID_misc->power.reset();
      // cores[i]->ifu->ID_misc->rt_power.reset();
      // cores[i]->ifu->ID_misc->power_t.reset();
      delete cores[i]->ifu->ID_inst;
      delete cores[i]->ifu->ID_operand;
      delete cores[i]->ifu->ID_misc;
      cores[i]->ifu->ID_inst = new inst_decoder(true, &interface_ip,
          cores[i]->ifu->coredynp.opcode_length, 1/*Decoder should not know how many by itself*/,
          cores[i]->ifu->coredynp.x86,
          Core_device, cores[i]->ifu->coredynp.core_ty);
      cores[i]->ifu->ID_operand = new inst_decoder(true, &interface_ip,
          cores[i]->ifu->coredynp.arch_ireg_width, 1,
          cores[i]->ifu->coredynp.x86,
          Core_device, cores[i]->ifu->coredynp.core_ty);
      cores[i]->ifu->ID_misc = new inst_decoder(true, &interface_ip,
          8/* Prefix field etc upto 14B*/, 1,
          cores[i]->ifu->coredynp.x86,
          Core_device, cores[i]->ifu->coredynp.core_ty);
      if (cores[i]->coredynp.predictionW>0) {
        cores[i]->ifu->BTB->power_t.reset();
        cores[i]->ifu->BTB->power.reset();
        cores[i]->ifu->BTB->rt_power.reset();
        cores[i]->ifu->BPT->power.reset();
        cores[i]->ifu->BPT->rt_power.reset();
        cores[i]->ifu->BPT->globalBPT->power_t.reset();
        cores[i]->ifu->BPT->globalBPT->power.reset();
        cores[i]->ifu->BPT->globalBPT->rt_power.reset();
        cores[i]->ifu->BPT->L1_localBPT->power_t.reset();
        cores[i]->ifu->BPT->L1_localBPT->power.reset();
        cores[i]->ifu->BPT->L1_localBPT->rt_power.reset();
        cores[i]->ifu->BPT->L2_localBPT->power_t.reset();
        cores[i]->ifu->BPT->L2_localBPT->power.reset();
        cores[i]->ifu->BPT->L2_localBPT->rt_power.reset();
        cores[i]->ifu->BPT->chooser->power_t.reset();
        cores[i]->ifu->BPT->chooser->power.reset();
        cores[i]->ifu->BPT->chooser->rt_power.reset();
        cores[i]->ifu->BPT->RAS->power_t.reset();
        cores[i]->ifu->BPT->RAS->power.reset();
        cores[i]->ifu->BPT->RAS->rt_power.reset();
      }
      cores[i]->lsu->power.reset();
      cores[i]->lsu->rt_power.reset();
      cores[i]->mmu->power.reset();
      cores[i]->mmu->rt_power.reset();
      cores[i]->exu->power.reset();
      cores[i]->exu->rt_power.reset();
      if (cores[i]->exu->exist){
        cores[i]->exu->rfu->power.reset();
        cores[i]->exu->rfu->rt_power.reset();
        cores[i]->exu->scheu->power.reset();
        cores[i]->exu->scheu->rt_power.reset();
        cores[i]->exu->exeu->power.reset();
        cores[i]->exu->exeu->rt_power.reset();
        if (cores[i]->exu->coredynp.num_fpus > 0) {
          cores[i]->exu->fp_u->power.reset();
          cores[i]->exu->fp_u->rt_power.reset();
          cores[i]->exu->fp_u->power_t.reset();
        }
        if (cores[i]->exu->coredynp.num_muls > 0) {
          cores[i]->exu->mul->power.reset();
          cores[i]->exu->mul->rt_power.reset();
          cores[i]->exu->mul->power_t.reset();
        }
        cores[i]->exu->bypass.power.reset();
        cores[i]->exu->bypass.rt_power.reset();
      }
      if (cores[i]->rnu->exist){
        cores[i]->rnu->power.reset();
        cores[i]->rnu->rt_power.reset();
      }
      if (XML->sys.Private_L2){
        cores[i]->l2cache->power.reset();
        cores[i]->l2cache->rt_power.reset();
      }
  }

  if (!XML->sys.Private_L2){
    if (numL2 >0){
      l2.power.reset();
      l2.rt_power.reset();
      for (i = 0;i < numL2; i++){
        l2array[i]->power.reset();
        l2array[i]->rt_power.reset();
      }
    }
  }

  if (numL3 >0){
    l3.power.reset();
    l3.rt_power.reset();
    for (i = 0;i < numL3; i++){
      l3array[i]->power.reset();
      l3array[i]->rt_power.reset();
    }
  }
    
  if (numL1Dir >0){
    l1dir.power.reset();
    l1dir.rt_power.reset();
    for (i = 0;i < numL1Dir; i++){
      l1dirarray[i]->power.reset();
      l1dirarray[i]->rt_power.reset();
    }
  }
    
  if (numL2Dir >0){
    l2dir.power.reset();
    l2dir.rt_power.reset();
    for (i = 0;i < numL2Dir; i++){
      l2dirarray[i]->power.reset();
      l2dirarray[i]->rt_power.reset();
    }
  }

  if (XML->sys.mc.number_mcs >0 && XML->sys.mc.memory_channels_per_mc>0){
    mc->power.reset();
    mc->rt_power.reset();
    mcs.power.reset();
    mcs.rt_power.reset();
    mc->frontend->power.reset();
    mc->frontend->rt_power.reset();
    mc->transecEngine->power.reset();
    mc->transecEngine->rt_power.reset();    
  }

  if (XML->sys.flashc.number_mcs >0 ){
    flashcontroller->power.reset();
    flashcontroller->rt_power.reset();
    flashcontrollers.power.reset();
    flashcontrollers.rt_power.reset();
  }

  if (XML->sys.niu.number_units >0){
    niu->power.reset();
    niu->rt_power.reset();
    nius.power.reset();
    nius.rt_power.reset();
  }

  if (XML->sys.pcie.number_units >0 && XML->sys.pcie.num_channels >0){
    pcie->power.reset();
    pcie->rt_power.reset();
    pcies.power.reset();
    pcies.rt_power.reset();
  }
  if (numNOC > 0){
    noc.power.reset();
    noc.rt_power.reset();
    for (i = 0;i < numNOC; i++){
      nocs[i]->power.reset();
      nocs[i]->rt_power.reset();
      if (nocs[i]->nocdynp.type){
        double temp_w = nocs[i]->area.get_w();
        double temp_h = nocs[i]->area.get_h();
        double temp_a = nocs[i]->area.get_area();
        delete nocs[i]->router;
        nocs[i]->init_router();
        nocs[i]->area.set_w(temp_w);
        nocs[i]->area.set_h(temp_h);
        nocs[i]->area.set_area(temp_a);
      }
      else{
        double temp_w = nocs[i]->area.get_w();
        double temp_h = nocs[i]->area.get_h();
        double temp_a = nocs[i]->area.get_area();
        delete nocs[i]->link_bus;
        nocs[i]->init_link_bus(sqrt(area.get_area()*XML->sys.NoC[i].chip_coverage));
        nocs[i]->area.set_w(temp_w);
        nocs[i]->area.set_h(temp_h);
        nocs[i]->area.set_area(temp_a);
      } 
    }
  }
}




void Processor::dump_stats(int plevel, ostream &out){
  int i;
  bool power_gating = XML->sys.power_gating;
  bool long_channel = XML->sys.longer_channel_device;
  for (i = 0;i < procdynp.numCore; i++){
    int j = procdynp.homoCore ? 0 : i;    
    double executionTime = cores[j]->coredynp.executionTime;
    double sum = 0;
    // // core
    // out<<cores[j]->get_power(executionTime, power_gating, long_channel)<<" ";
    if (cores[j]->ifu->exist){
      // // IFU, instruction fetch unit
      // out<<cores[j]->ifu->get_power(executionTime, power_gating, long_channel)<<" ";
      // IC, instruction cache
      out<<cores[j]->ifu->icache.get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->ifu->icache.get_power(executionTime, power_gating, long_channel);
      if (cores[j]->coredynp.predictionW>0){
        // BTB, branch target buffer
        out<<cores[j]->ifu->BTB->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->ifu->BTB->get_power(executionTime, power_gating, long_channel);
        if (cores[j]->ifu->BPT->exist){
          // BP, branch predictor
          out<<cores[j]->ifu->BPT->get_power(executionTime, power_gating, long_channel)<<" ";
          sum +=cores[j]->ifu->BPT->get_power(executionTime, power_gating, long_channel);
        }
      }
      // IB, instruction buffer
      out<<cores[j]->ifu->IB->get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->ifu->IB->get_power(executionTime, power_gating, long_channel);
      // ID, instruction decoder
      double id_power = cores[j]->ifu->ID_inst->get_power(executionTime, power_gating, long_channel)
                      + cores[j]->ifu->ID_misc->get_power(executionTime, power_gating, long_channel)
                      + cores[j]->ifu->ID_operand->get_power(executionTime, power_gating, long_channel);
      out<<id_power<<" ";
      sum+=id_power;
    }
    if (cores[j]->coredynp.core_ty==OOO){
      if (cores[j]->rnu->exist){
        // REN, renaming unit
        out<<cores[j]->rnu->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->rnu->get_power(executionTime, power_gating, long_channel);
      }
    }
    if (cores[j]->lsu->exist){
     //  LSU, load store unit
     //  out<<cores[j]->lsu->get_power(executionTime, power_gating, long_channel)<<" ";
      // DC, data cache
      out<<cores[j]->lsu->dcache.get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->lsu->dcache.get_power(executionTime, power_gating, long_channel);
      if (cores[j]->coredynp.core_ty==Inorder){
        // out<<"Load/Store_Queue_"<<j<<" ";
        out<<cores[j]->lsu->LSQ->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->lsu->LSQ->get_power(executionTime, power_gating, long_channel);
      }else{
        if (XML->sys.core[cores[j]->lsu->ithCore].load_buffer_size >0){
          // out<<"LoadQ_"<<j<<" ";
          out<<cores[j]->lsu->LoadQ->get_power(executionTime, power_gating, long_channel)<<" ";
          sum +=cores[j]->lsu->LoadQ->get_power(executionTime, power_gating, long_channel);
        }else{
          double LQ_power =  cores[j]->lsu->dcache.get_power(executionTime, power_gating, long_channel)
               - cores[j]->lsu->LSQ->get_power(executionTime, power_gating, long_channel)
               - cores[j]->lsu->dcache.get_power(executionTime, power_gating, long_channel);
          if(LQ_power < 0) LQ_power = 0;
          out<<LQ_power<<" ";
          sum +=LQ_power;
        }
        // out<<"StoreQ_"<<j<<" "; // ?
        out<<cores[j]->lsu->LSQ->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->lsu->LSQ->get_power(executionTime, power_gating, long_channel);
      }
    }
    if (cores[j]->mmu->exist){
      // MMU, memory management unit
      out<<cores[j]->mmu->get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->mmu->get_power(executionTime, power_gating, long_channel);
    }
    if(cores[j]->exu->exist){
     // //  EXU, execution unit
     //  out<<cores[j]->exu->get_power(executionTime, power_gating, long_channel)<<" ";      
     //  // RF, register file
     //  out<<cores[j]->exu->rfu->get_power(executionTime, power_gating, long_channel)<<" ";
      // IRF, Int register file
      out<<cores[j]->exu->rfu->IRF->get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->exu->rfu->IRF->get_power(executionTime, power_gating, long_channel);
      // FPRF, float register file
      out<<cores[j]->exu->rfu->FRF->get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->exu->rfu->FRF->get_power(executionTime, power_gating, long_channel);
     //  if (cores[j]->coredynp.regWindowing){
     //    // Register Windows
     //    out<<cores[j]->exu->rfu->RFWIN->get_power(executionTime, power_gating, long_channel)<<" ";
     //  }
     //  // Instruction Scheduler
     //  out<<cores[j]->exu->scheu->get_power(executionTime, power_gating, long_channel)<<" ";
      if (cores[j]->coredynp.core_ty==OOO){
        // IW, Int Instruction Window
        out<<cores[j]->exu->scheu->int_inst_window->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->exu->scheu->int_inst_window->get_power(executionTime, power_gating, long_channel);
        // FPIW, FP Instruction Window
        out<<cores[j]->exu->scheu->fp_inst_window->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->exu->scheu->fp_inst_window->get_power(executionTime, power_gating, long_channel);
        if (XML->sys.core[cores[j]->exu->ithCore].ROB_size >0){
          // ROB 
          out<<cores[j]->exu->scheu->ROB->get_power(executionTime, power_gating, long_channel)<<" ";
          sum +=cores[j]->exu->scheu->ROB->get_power(executionTime, power_gating, long_channel);
        }else{
         out<<0<<" ";
        }
      }else if(cores[j]->coredynp.multithreaded){
        // IW, instruction window
        out<<cores[j]->exu->scheu->int_inst_window->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->exu->scheu->int_inst_window->get_power(executionTime, power_gating, long_channel);
      }
      // IALU
      out<<cores[j]->exu->exeu->get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->exu->exeu->get_power(executionTime, power_gating, long_channel);
      if (cores[j]->coredynp.num_fpus>0){
        // FPU
        out<<cores[j]->exu->fp_u->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->exu->fp_u->get_power(executionTime, power_gating, long_channel);
      }
      if (cores[j]->coredynp.num_muls>0){
        // CALU, complex ALU
        out<<cores[j]->exu->mul->get_power(executionTime, power_gating, long_channel)<<" ";
        sum +=cores[j]->exu->mul->get_power(executionTime, power_gating, long_channel);
      }
      // RBB, result broadcast bus
      out<<cores[j]->exu->bypass.get_power(executionTime, power_gating, long_channel)<<" ";
      sum +=cores[j]->exu->bypass.get_power(executionTime, power_gating, long_channel);
    }
    if (XML->sys.Private_L2){
      // out<<cores[j]->l2cache->cachep.name<<"_"<<j<<" ";
      out<<cores[j]->l2cache->get_power(1, power_gating, long_channel)<<" ";
      sum +=cores[j]->l2cache->get_power(1, power_gating, long_channel);
    }
    double other_power = cores[j]->get_power(executionTime, power_gating, long_channel) - sum;
    out<< ((other_power>0) ? other_power : 0) <<" ";
  }
  
  if (!XML->sys.Private_L2){      
    double l2_power = 0;
    out<<l2.get_power(1, power_gating, long_channel)<<" ";
  }

  if(XML->sys.number_of_custom_blocks > 0){
    out<<CIM_SRAM.power<<" ";
  }
  
  out<<endl;
  return;
}

void Processor::dump_name(ostream &out){
  int i;
  for (i = 0;i < procdynp.numCore; i++){
    int j = procdynp.homoCore ? 0 : i;
    // out<<"C"<<i<<" ";
    if (cores[j]->ifu->exist){
     //  out << "Instruction_Fetch_Unit_"<<j<<" ";
      out << "C"<<i<<"_IC\t";
      if (cores[j]->coredynp.predictionW>0){
        out<<"C"<<i<<"_BTB\t";
        if (cores[j]->ifu->BPT->exist){
          out<<"C"<<i<<"_BP\t";
        }
      }
      out<<"C"<<i<<"_IB ";
      out<<"C"<<i<<"_ID ";
    }
    if (cores[j]->coredynp.core_ty==OOO){
      if (cores[j]->rnu->exist){
        out<<"C"<<i<<"_REN ";
      }
    }
    if (cores[j]->lsu->exist){
     //  out<<"Load_Store_Unit_"<<j<<" ";
      out<<"C"<<i<<"_DC ";
      if (cores[j]->coredynp.core_ty==Inorder){
        out<<"C"<<i<<"_LSQ ";
      }else{
        if (XML->sys.core[cores[j]->lsu->ithCore].load_buffer_size >0){
          out<<"C"<<i<<"_LQ ";
        }else{
         out<<"C"<<i<<"_LQ ";
        }
        out<<"C"<<i<<"_SQ ";
      }
    }
    if (cores[j]->mmu->exist){
      out<<"C"<<i<<"_MMU ";
    }
    if(cores[j]->exu->exist){
     //  out<<"Execution_Unit_"<<j<<" ";
     //  out<<"Register_Files_"<<j<<" ";
      out<<"C"<<i<<"_IRF ";
      out<<"C"<<i<<"_FPRF ";
     //  if (cores[j]->coredynp.regWindowing){
     //    out<<"Register_Windows_"<<j<<" ";
     //  }
     //  out<<"Instruction_Scheduler_"<<j<<" ";
      if (cores[j]->coredynp.core_ty==OOO){
        out<<"C"<<i<<"_IW ";
        out<<"C"<<i<<"_FPIW ";
       //  if (XML->sys.core[cores[j]->exu->ithCore].ROB_size >0){
          out<<"C"<<i<<"_ROB ";
       //  }
      }else if(cores[j]->coredynp.multithreaded){
       out<<"C"<<i<<"_IW ";
     }
      out<<"C"<<i<<"_IALU ";
      if (cores[j]->coredynp.num_fpus>0){
        out<<"C"<<i<<"_FPU ";
      }
      if (cores[j]->coredynp.num_muls>0){
       out<<"C"<<i<<"_CALU ";         
      }
      out<<"C"<<i<<"_RBB ";
    }
    if (XML->sys.Private_L2){
      out<<"C"<<i<<"_L2 ";
    }
    out<<"C"<<i<<"_Other ";
  }

  if (!XML->sys.Private_L2){      
    out<<"L2_shared ";
  }

  if(XML->sys.number_of_custom_blocks > 0){
    out<<CIM_SRAM.name<<" ";
  }

  out<<endl;
  return;
}



void Processor::dump_area(ostream &out){
  int i;
  for (i = 0;i < procdynp.numCore; i++){
    int j = procdynp.homoCore ? 0 : i;
    // IFU
    if (cores[j]->ifu->exist){
      out<<cores[j]->ifu->icache.area.get_area()<<" ";
      if (cores[j]->coredynp.predictionW>0){
        out<<cores[j]->ifu->BTB->area.get_area()<<" ";
        if (cores[j]->ifu->BPT->exist){
          out<<cores[j]->ifu->BPT->area.get_area()<<" ";
        }
      }
      out<<cores[j]->ifu->IB->area.get_area()<<" ";
      out<<cores[j]->ifu->ID_inst->area.get_area()
         + cores[j]->ifu->ID_misc->area.get_area()
         + cores[j]->ifu->ID_operand->area.get_area()<<" ";
    }
    // RNU
    if (cores[j]->coredynp.core_ty==OOO){
      if (cores[j]->rnu->exist){
        out<<cores[j]->rnu->area.get_area()<<" ";
      }
    }

    // LSU  
    if (cores[j]->lsu->exist){
      out<<cores[j]->lsu->dcache.area.get_area()<<" ";
      if (cores[j]->coredynp.core_ty==Inorder){
        out<<0<<" ";
        out<<cores[j]->lsu->LSQ->area.get_area()<<" ";
      }else{
        if (XML->sys.core[cores[j]->lsu->ithCore].load_buffer_size >0){
          out<<cores[j]->lsu->LoadQ->area.get_area()<<" ";
        } else {
          out<<0<<" ";
        }
        out<<cores[j]->lsu->LSQ->area.get_area()<<" ";
      }
    }

    // MMU
    if (cores[j]->mmu->exist){
      out<<cores[j]->mmu->area.get_area()<<" ";
    }
    // EXU
    if(cores[j]->exu->exist){
      out<<cores[j]->exu->rfu->IRF->area.get_area()<<" ";
      out<<cores[j]->exu->rfu->FRF->area.get_area()<<" ";
     //  if (cores[j]->coredynp.regWindowing){
     //    out<<"Register_Windows_"<<j<<" ";
     //  }
     //  out<<"Instruction_Scheduler_"<<j<<" ";
      if (cores[j]->coredynp.core_ty==OOO){
        out<<cores[j]->exu->scheu->int_inst_window->area.get_area()<<" ";
        out<<cores[j]->exu->scheu->fp_inst_window->area.get_area()<<" ";
        if (XML->sys.core[cores[j]->exu->ithCore].ROB_size >0){
          out<<cores[j]->exu->scheu->ROB->area.get_area()<<" ";
        }else{
          out<<0<<" ";
        }
      }else if(cores[j]->coredynp.multithreaded){
        out<<cores[j]->exu->scheu->int_inst_window->area.get_area()<<" ";
      }
      out<<cores[j]->exu->exeu->area.get_area()<<" ";
      if (cores[j]->coredynp.num_fpus>0){
        out<<cores[j]->exu->fp_u->area.get_area()<<" ";
      }
      if (cores[j]->coredynp.num_muls>0){
        out<<cores[j]->exu->mul->area.get_area()<<" ";
      }
      out<<cores[j]->exu->bypass.area.get_area()<<" ";
    }

    if (XML->sys.Private_L2){
      out<<cores[j]->l2cache->area.get_area()<<" ";
    }
    out<<cores[j]->undiffCore->area.get_area()<<" ";
  }

  if (!XML->sys.Private_L2){      
    out<<l2.area.get_area()<<" ";
  }

  if(XML->sys.number_of_custom_blocks > 0){
    out<<CIM_SRAM.area<<" ";
  }

  out<<endl;
  return;
}

void Processor::dump_hier_area(ostream &out){
  int i;
  for (i = 0;i < procdynp.numCore; i++){
    int j = procdynp.homoCore ? 0 : i;
    out<<"C"<<i<<endl;
    out<<"Area = "<<cores[j]->area.get_area()<<"mm^2"<<endl;
    // IFU
    if (cores[j]->ifu->exist){
      out<<"    C"<<i<<"_IFU"<<endl;
      out<<"    Area = "<<cores[j]->ifu->icache.area.get_area()<<"mm^2"<<endl;
      if (cores[j]->coredynp.predictionW>0){
        out<<"        C"<<i<<"_BTB"<<endl;
        out<<"        Area = "<<cores[j]->ifu->BTB->area.get_area()<<"mm^2"<<endl;
        if (cores[j]->ifu->BPT->exist){
          out<<"        C"<<i<<"_BP"<<endl;
          out<<"        Area = "<<cores[j]->ifu->BPT->area.get_area()<<"mm^2"<<endl;
        }
      }
      out<<"       C"<<i<<"_IB"<<endl;
      out<<"        Area = "<<cores[j]->ifu->IB->area.get_area()<<"mm^2"<<endl;
      out<<"       C"<<i<<"_IB"<<endl;
      out<<"        Area = "<<cores[j]->ifu->ID_inst->area.get_area()
         + cores[j]->ifu->ID_misc->area.get_area()
         + cores[j]->ifu->ID_operand->area.get_area()<<"mm^2"<<endl;
    }
    // RNU
    if (cores[j]->coredynp.core_ty==OOO){
      if (cores[j]->rnu->exist){
        out<<"    C"<<i<<"_RNU"<<endl;
        out<<"    Area = "<<cores[j]->rnu->area.get_area()<<"mm^2"<<endl;
      }
    }
    // LSU  
    out<<"    C"<<i<<"_LSU"<<endl;
    out<<"    Area = "<<cores[j]->lsu->area.get_area()<<"mm^2"<<endl;
    if (cores[j]->lsu->exist){
      out<<"        C"<<i<<"_DC"<<endl;
      out<<"        Area = "<<cores[j]->lsu->dcache.area.get_area()<<"mm^2"<<endl;
      if (cores[j]->coredynp.core_ty==Inorder){
        out<<"        C"<<i<<"_LoadQ"<<endl;
        out<<"        Area = "<<0<<"mm^2"<<endl;
        out<<"        C"<<i<<"_StoreQ"<<endl;
        out<<"        Area = "<<cores[j]->lsu->LSQ->area.get_area()<<"mm^2"<<endl;
      }else{
        if (XML->sys.core[cores[j]->lsu->ithCore].load_buffer_size >0){
          out<<"        C"<<i<<"_LoadQ"<<endl;
          out<<"        Area = "<<cores[j]->lsu->LoadQ->area.get_area()<<"mm^2"<<endl;
        } else {
          out<<"        C"<<i<<"_LoadQ"<<endl;
          out<<"        Area = "<<0<<"mm^2"<<endl;
        }
        out<<"        C"<<i<<"_StoreQ"<<endl;
        out<<"        Area = "<<cores[j]->lsu->LSQ->area.get_area()<<"mm^2"<<endl;
      }
    }

    // MMU
    if (cores[j]->mmu->exist){
      out<<"    C"<<i<<"_MMU"<<endl;
      out<<"    Area = "<<cores[j]->mmu->area.get_area()<<"mm^2"<<endl;
    }
    // EXU
    out<<"    C"<<i<<"_EXU"<<endl;
    out<<"    Area = "<<cores[j]->exu->area.get_area()<<"mm^2"<<endl;
    if(cores[j]->exu->exist){
      out<<"        C"<<i<<"_IRF"<<endl;
      out<<"        Area = "<<cores[j]->exu->rfu->IRF->area.get_area()<<"mm^2"<<endl;
      out<<"        C"<<i<<"_FPRF"<<endl;
      out<<"        Area = "<<cores[j]->exu->rfu->FRF->area.get_area()<<"mm^2"<<endl;
     //  if (cores[j]->coredynp.regWindowing){
     //    out<<"Register_Windows_"<<j<<" ";
     //  }
     //  out<<"Instruction_Scheduler_"<<j<<" ";
      if (cores[j]->coredynp.core_ty==OOO){
        out<<"        C"<<i<<"_IW"<<endl;
        out<<"        Area = "<<cores[j]->exu->scheu->int_inst_window->area.get_area()<<"mm^2"<<endl;
        out<<"        C"<<i<<"_FPIW"<<endl;
        out<<"        Area = "<<cores[j]->exu->scheu->fp_inst_window->area.get_area()<<"mm^2"<<endl;
        if (XML->sys.core[cores[j]->exu->ithCore].ROB_size >0){
          out<<"        C"<<i<<"_ROB"<<endl;          
          out<<"        Area = "<<cores[j]->exu->scheu->ROB->area.get_area()<<"mm^2"<<endl;
        }else{
          out<<"        C"<<i<<"_ROB"<<endl;
          out<<"        Area = "<<0<<"mm^2"<<endl;
        }
      }else if(cores[j]->coredynp.multithreaded){
        out<<"        C"<<i<<"_IW"<<endl;
        out<<"        Area = "<<cores[j]->exu->scheu->int_inst_window->area.get_area()<<"mm^2"<<endl;
      }
      out<<"        C"<<i<<"_IALU"<<endl;      
      out<<"        Area = "<<cores[j]->exu->exeu->area.get_area()<<"mm^2"<<endl;
      if (cores[j]->coredynp.num_fpus>0){
        out<<"        C"<<i<<"_FAPU"<<endl;      
        out<<"        Area = "<<cores[j]->exu->fp_u->area.get_area()<<"mm^2"<<endl;
      }
      if (cores[j]->coredynp.num_muls>0){
        out<<"        C"<<i<<"_CALU"<<endl;      
        out<<"        Area = "<<cores[j]->exu->mul->area.get_area()<<"mm^2"<<endl;
      }
      out<<"        C"<<i<<"_RBB"<<endl;      
      out<<"        Area = "<<cores[j]->exu->bypass.area.get_area()<<"mm^2"<<endl;
    }

    if (XML->sys.Private_L2){
      out<<"    C"<<i<<"_L2"<<endl;      
      out<<"    Area = "<<cores[j]->l2cache->area.get_area()<<"mm^2"<<endl;
    }
    out<<"    C"<<i<<"_Other"<<endl;      
    out<<"    Area = "<<cores[j]->undiffCore->area.get_area()<<"mm^2"<<endl;  
  }

  if (!XML->sys.Private_L2){      
    out<<"L2_shared"<<endl;      
    out<<"Area = "<<l2.area.get_area()<<"mm^2"<<endl;  
  }

  if(XML->sys.number_of_custom_blocks > 0){
    out<<CIM_SRAM.name<<endl;      
    out<<"Area = "<<CIM_SRAM.area<<"mm^2"<<endl;
  }
  return;
}
