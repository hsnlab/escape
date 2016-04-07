/* hwloc2nffg
 *
 * Converts hwloc data (hierarchical map of computing and network elements)
 * to an NFFG representation in JSON format. This data can be processed by
 * an orchestrator.
 *
 * Written by Andras Majdan.
 * Email: majdan.andras@gmail.com
 */

#include <iostream>
#include <string>
#include <boost/program_options.hpp>
#include <jsoncpp/json/json.h>
#include <hwloc.h>
#include <sys/utsname.h>

using namespace std;

namespace po = boost::program_options;

// TODO: git versioning
const string version = "unknown";

class ID
{
	private:
	unsigned int lastfreeid=0;

	public:
	map<string, unsigned int> lastfreeidfortype;

	unsigned int get_next_id_for_type(string nodetype)
	{
		unsigned int n;

		if(lastfreeidfortype.find(nodetype) == lastfreeidfortype.end())
			lastfreeidfortype.insert(make_pair(nodetype, 0));

		n = lastfreeidfortype[nodetype];
		lastfreeidfortype[nodetype] += 1;
		return n;
	}

	unsigned int get_next_global_id()
	{
		return lastfreeid++;
	}
};

void add_parameters(Json::Value &root)
{
	struct utsname unamedata;
	uname(&unamedata);

	root["id"] = unamedata.nodename;
	root["name"] = string("NFFG-") + string(unamedata.nodename);

	// TODO: real versioning
	root["version"] = "1.0";
}

// Check if node is a network sap
bool network_sap(hwloc_obj_t node)
{
	if(node->type==HWLOC_OBJ_OS_DEVICE)
	{
		int num_of_infos = node->infos_count;

		for(int info_i=0; info_i<num_of_infos; info_i++)
			if(!strcasecmp(node->infos[info_i].name, "address"))
				return true;
	}
	return false;
}

// Check if node is required (based on node's type)
bool required_by_type(hwloc_obj_t node)
{
	hwloc_obj_type_t type = node->type;

	if (type == HWLOC_OBJ_PU)
		return true;
	else if (type == HWLOC_OBJ_OS_DEVICE)
		return network_sap(node);
	else
		return false;
}

string get_node_type(hwloc_obj_t obj)
{
	char ctype[32];
	string type;

	hwloc_obj_type_snprintf(ctype, sizeof(ctype), obj, 0);
	type = string(ctype);

	return type;
}

string get_node_name(hwloc_obj_t obj, ID &id)
{
	if ( network_sap(obj) && obj->name != NULL)
		return string(obj->name);

	string type = get_node_type(obj);

	if ( (obj->type == HWLOC_OBJ_PU || obj->type == HWLOC_OBJ_CORE ||
		  obj->type == HWLOC_OBJ_MACHINE) &&
		  (obj->os_index != (unsigned) -1) )
		return type + "#" + to_string(obj->os_index);
	else
		return type + "!" + to_string(id.get_next_id_for_type(type));
}

typedef deque<pair<unsigned int, string>*> NodePorts;

// Process nodes
NodePorts *add_nodes(
	Json::Value &node_infras,
	Json::Value &node_saps,
	Json::Value &node_edges,
	ID &id,
	hwloc_topology_t &topology,
	hwloc_obj_t obj,
	int depth)
{
	auto *allports = new deque<NodePorts*>;

	for (unsigned int i = 0; i < obj->arity; i++) {
		auto *ports = add_nodes(node_infras, node_saps,
			node_edges, id, topology, obj->children[i], depth + 1);
		if (ports != NULL)
			allports->push_back(ports);
    }

    if (!allports->empty() || required_by_type(obj))
    {
		Json::Value node;
		Json::Value ports;

		string node_name = get_node_name(obj, id);
		node["id"] = node["name"] = node_name;

		if (!allports->empty())
		{
			for (auto ait = allports->begin(); ait != allports->end(); ait++)
			{
				for (auto pit = (*ait)->begin(); pit != (*ait)->end(); pit++)
				{
					Json::Value edge;
					unsigned int port_gid;

					edge["id"] = id.get_next_global_id();
					edge["src_node"] = node_name;
					port_gid = id.get_next_global_id();
					edge["src_port"] = port_gid;
					edge["dst_node"] = (*pit)->second;
					edge["dst_port"] = (*pit)->first;
					edge["delay"] = 0.1;
					edge["bandwidth"] = 1000;
					node_edges.append(edge);

					Json::Value portid;
					portid["id"] = port_gid;
					ports.append(portid);
				}
			}
		}

		Json::Value portid;
		unsigned int port_gid = id.get_next_global_id();
		portid["id"] = port_gid;
		ports.append(portid);

		if (network_sap(obj))
		{
			Json::Value sap;
			sap["id"] = sap["name"] = node_name;
			sap["ports"] = ports;
			node_saps.append(sap);
		}
		else
		{
			Json::Value node;
			node["id"] = node["name"] = node_name;
			node["ports"] = ports;
			node["domain"] = "INTERNAL";

			if (obj->type == HWLOC_OBJ_PU)
			{
				Json::Value supported;
				supported.append("headerDecompressor");
				node["type"] = "EE";
				node["supported"] = supported;
				Json::Value res;
				res["cpu"] = 1;
				res["mem"] = 32000;
				res["storage"] = 150;
				res["delay"] = 0.5;
				res["bandwidth"]= 1000;
				node["resources"] = res;
			}
			else
			{
				node["type"] = "SDN-SWITCH";
				Json::Value res;
				res["cpu"] = 0;
				res["mem"] = 0;
				res["storage"] = 0;
				res["delay"] = 0.5;
				res["bandwidth"]= 1000;
				node["resources"] = res;
			}
			node_infras.append(node);
		}

		auto *node_ports = new NodePorts;
		auto *pair_to_push = new pair<unsigned int, string>(port_gid, node_name);
		node_ports->push_back(pair_to_push);
		return node_ports;
	}

	return NULL;
}

void add_topology_tree(Json::Value &root)
{
	hwloc_topology_t topology;

	// Allocate and initialize topology object.
	hwloc_topology_init(&topology);

	// Add PCI devices for detection
	hwloc_topology_set_flags(topology, HWLOC_TOPOLOGY_FLAG_IO_DEVICES);

	// Perform the topology detection.
	hwloc_topology_load(topology);

	// Add NFFG parameters
	Json::Value parameters;
	add_parameters(parameters);
	root["parameters"] = parameters;

	ID id;
	Json::Value node_infras, node_saps, node_edges;

	add_nodes(node_infras, node_saps, node_edges,
		id, topology, hwloc_get_root_obj(topology), 0);

	root["node_saps"] = node_saps;
	root["node_infras"] = node_infras;
	root["edge_links"] = node_edges;
}

int main(int argc, char* argv[])
{
	po::options_description desc("Allowed options");
	desc.add_options()
		("help", "Prints help message")
		("version", "Prints version number")
	;

	po::variables_map vm;
	po::store(po::parse_command_line(argc, argv, desc), vm);
	po::notify(vm);

	if (vm.count("help")) {
		cout << desc << endl;
		return 0;
	}

	if (vm.count("version")) {
		cout << "Version " << version << endl;
		return 0;
	}

	Json::Value root;
	add_topology_tree(root);

	Json::StyledWriter writer;
	string json_string = writer.write(root);
	cout << json_string;
	return 0;
}


