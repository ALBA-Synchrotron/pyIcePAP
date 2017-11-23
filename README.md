How to define an python profile based on pyIcePAP module
--------------------------------------------------------

Following these steps you will create an ipython profile for easy access to an IncePAP system.
The profile exposes several monitor and configuration functions.

1. Create a default ipython profile name ipapconsole (for instance):

        ipython profile create ipapconsole

2. Open the profile_ipapconsole/ipython_config.py and add the lines:

        from pkg_resources import resource_filename
        c.InteractiveShellApp.exec_files = [resource_filename('pyIcePAP', 'ipapconsole.ipy')]

3. Then you can load the profile by:

        ipython --profile=ipapconsole
 
