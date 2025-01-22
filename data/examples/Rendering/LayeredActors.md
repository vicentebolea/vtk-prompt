### Description

Demonstrates the use of two renderers in a render window. Notice that the second (and subsequent) renderers will have a transparent background.

The first layer (layer 0) contains the base object, a slab in this case. The second layer (layer 1) contains an object (axes in this case). This axes object will always be in front of the base layer object. When the program runs, the top-most layer will be the active layer, layer 1 in this case.

Two callbacks are provided, the first callback selects which layer is active:

- Pressing **0** on the keyboard will let you manipulate the objects in layer 0.
- Pressing **1** on the keyboard will let you manipulate the objects in layer 1.

The second callback allows you to orient objects in all layers using the object in the active layer.

!!! note
    Objects in the top-most layer will always be in front of any objects in other layers.

!!! info
    This is an extension of the [TransparentBackground.py](../TransparentBackground) example, extended by adding an extra callback so that the non-active layer objects move in conjunction with the active layer objects.
