### McPAT 1.3 Modified.

What's modified?

1. Initialization phase and computation phase are decoupled.
   
   - Initialization of a processor is done directly in the instantiation of it.
   
   - Area computing is left unchanged in initialization (a chip is just a chip, not a transformer)
   
   - Power computing is picked out into a new function, `compute`.

2. Consecutive simulation is enabled.
   
   - Modified McPAT can initialize for just once and keep computing new power stats upon new XML files.

3. **2025.2.10** Output Format is Modified for Hotspot
   
   All power breakdowns are summarized. 

4. **2025.2.11** Interface for Custom Blocks.
   
   A very simple interface added. You can see two new files "custom_block.cc" & "custom_block.h", which contains a very simple definition. An example is instantiated as "CIM_SRAM" under "processor" at "processor.h" & "processor.cc".
   
   

How to use?

- The command of original McPAT is **still supported**.
  
  ```shell
  mcpat -infile <name> -print_level <0~5> -opt_for_clk <0/1>
  ```

- To enable consecutive simulation, use command `-trace`.
  
  So the command becomes:
  
  ```shell
  mcpat -trace -infile <name> -print_level <0~5> -opt_for_clk <0/1>
  ```
  
  After simulating upon the initial XML file, McPAT waits for you to input a new filename. This continues until you input "exit" and ends the program.
  
  If you input "repeat", McPAT computes upon the last XML interface.

- Cutsom Blocks
  
  Now, you can already see the power stat of "CIM_SRAM" whatever benchmark you're using (but the value is crazy, since the detailed computation is not specified).
  
  To write a more realistic computation for it, you have to read three parts:
  
  1. The simple definition in "custom_block.h".
  
  2. The instantiation of it in "processor.h".
  
  3. The calculation for it in "processor.cc". It's at the beginning of `void Processor::compute(ParseXML *fresh_XML)`. 




