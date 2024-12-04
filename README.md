# Pixel Life

A comprehensive simulation of a "cell ecosystem" using the pygame library. 
It incorporates various features such as cell movement, reproduction, hunger, stamina, obstacle interactions, and visual debugging.

The simulation is highly extensible.

## To-Do:
- More genetic traits
- Path finding around objects
- Limit visual range (genetic trait)
- Balance out default values
- More hotkeys (disable hunger/stamina costs, disable mate timer, etc)
- Add zoom in/out function
- Despawn timer for old food cells


### Bugs:
- Sometimes cells will hug the border of the grid and multiply infinite times. Should be fixed with path finding.
- Food can spawn inside obstacles causing cells to run into them untill theyre dead.
