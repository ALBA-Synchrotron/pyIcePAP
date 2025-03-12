def get_axes(icepap, axes_str: str):
    """
    Method to convert axes string on axes objects
    :param axes_str:
    :return:
    """
    axes_str = axes_str.strip()
    if axes_str == "all":
        axes = icepap.find_axes(only_alive=False)
    elif axes_str == "alive":
        axes = icepap.find_axes(only_alive=True)
    else:
        axes = []
        for axis in axes_str.split(","):
            try:
                axes.append(int(axis))
            except ValueError:
                axes.append(axis.strip())
        axes.sort()
    return icepap[axes]