The nffglib.py implements the Python classes corresponding to ../specification/virtualizer.yang, as well as xml parser/dumper.
The high level overview of the communication is:

0, The Agent (e.g. infrastructure domain) creates the view of the domain in the form of an nffglib.Virtualizer instance. (This can be e.g. parsed from an xml file or build up from elementary instances.)

1, The Manager (e.g. higher level orchestrator) queries the infrastructure view with a netconf-like "get-config" command.

2, The Agent responses to the Manager with the xml dump of it's Virtualizer instance.

3, The Manager parses the received config to a Virtualizer instance.

4, The Manager modifies (e.g. adds NFs, flow entries) the local instance.

5, The Manager sends the xml dump of the requested configuration to the Agent with a netconf-like "edit-config" command.

6, The Agent parses the received requested config and applies (installs NFs, forwarding rules)


Examples realizing the communication above can be found in "Example_http" and in the "Example_tcp_socket" directory.