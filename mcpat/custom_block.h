#ifndef __CUSTOM_BLOCK_H__
#define __CUSTOM_BLOCK_H__

#include "XML_Parse.h"

/**
 * A very simple interface to add custom blocks.alignas
 * 
 * 2 ways to compute power:
 *  either P_dynamic = switching_energy * f * activity_factor 
 *  or     P_dynamic = switching_energy * switch_count / time_interval
 * 
 * If you need a better computation method, write new functions to 
 * overwrite the weak functions declared here.
 */
class CustomBlock
{
 public:
  double static_power;
  double switching_energy; 
  double power;
  double area;
  string name;

  CustomBlock(string name_ = "Custom", double static_ = 0, double switch_ = 0):
  name(name_), static_power(static_), switching_energy(switch_) {power = 0;}

  __attribute__((weak)) 
  double computePower_Frequency(double frequency, double activity_factor){
    power = static_power + frequency*activity_factor*switching_energy;
    return static_power + frequency*activity_factor*switching_energy;
  }
  
  __attribute__((weak)) 
  double computePower_Interval(int switch_count, double interval){
    power = static_power + switch_count*switching_energy/interval;
    return static_power + switch_count*switching_energy/interval;
  }

  void displayPower(){
    cout<<name<<" "<<power<<endl;
    return;
  }

  ~CustomBlock(){};
};
#endif