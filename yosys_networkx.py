import os
import networkx as nx
import pydotplus
import matplotlib.pyplot as plt
import itertools
import shutil
import tempfile

def verilog2networkx(infile, synthesize=True, pngfile=None, dotfile=None):
  """Convert a verilog file to a networkx network, using yosys

  Keyword arguments:
  infile -- Verilog filename
  synthesize -- synthesize using ABC (default: True)
  pngfile -- filename to save a PNG of the Yosys network (default: None)
  dotfile -- filename to save a GraphVis of the Yosys network (default: None)

  Example:
  >>> G1 = verilog2networkx('counter.v', synthesize=False)
  >>> list(G1.nodes)
  ['c12', 'v0', 'n7', 'n8', 'n6', 'c16', 'n5', 'c18', 'v1', 'c19']
  >>> G2 = verilog2networkx('counter.v', pngfile='counter.png', dotfile='counter.dot')
  >>> list(G2.nodes)
  ['c60', 'c46', 'c58', 'c61', 'c56', 'c57', 'c59', 'n32', 'n3', 'n31', 'n27', 'c51', 'n33', 'c44', 'n5', 'n14', 'c50', 'n7', 'n23', 'c55', 'c68', 'c49', 'c40', 'c41', 'c48', 'n13', 'c39', 'n28', 'c66', 'c36', 'c52', 'c43', 'n29', 'n12', 'c47', 'n2', 'c37', 'c45', 'c65', 'n30', 'c67', 'c54', 'c53', 'c42']
  """

  tmpdir = tempfile.mkdtemp()
  command = """
  read_verilog %s
  proc; opt; fsm; opt; memory; opt
  """ % infile
  if synthesize:
    command = command + """
    techmap; opt
    dfflibmap -liberty cmos_cells.lib
    abc -liberty cmos_cells.lib
    splitnets -ports; opt
    read_liberty -lib cmos_cells.lib
    """
  command = command + """
  show -format dot -prefix %s/yosys
  show -format png -prefix %s/yosys
  """ % (tmpdir, tmpdir)

  try:
    os.system('yosys -p "%s"' % command)

    if pngfile:
      shutil.copyfile(tmpdir+"/yosys.png", pngfile)
    if dotfile:
      shutil.copyfile(tmpdir+"/yosys.dot", dotfile)

    os.system('sed -i "s/:[^ ]*//g" %s/yosys.dot' % tmpdir)

    with open('%s/yosys.dot' % tmpdir) as f:
      s = f.read()
    g = pydotplus.parser.parse_dot_data(s)
    G = nx.nx_pydot.from_pydot(g)
  finally:
    shutil.rmtree(tmpdir)
  return G

def remove_nodes(G, nodelist):
  """Remove nodes from a networkx DiGraph, without removing the connecting 
  edges, and return the resulting DiGraph.

  First creates new edges to route around the specified nodes, then deletes the
  nodes.

  Keyword arguments:
  G -- a networkx graph
  nodelist --- list of networkx node identifiers to be removed

  Example:
  >>> import networkx as nx
  >>> G = nx.DiGraph()
  >>> G.add_edges_from([(1,2),(2,3),(3,4),(4,2)])  
  >>> newG = remove_nodes(G, [2])
  >>> newG.edges
  OutEdgeView([(1, 3), (3, 4), (4, 3)])
  """
  for node in nodelist:
    # reroute around each target node
    new_edges = itertools.product(G.predecessors(node), G.successors(node))
    G.add_edges_from(new_edges)
  # delete target nodes
  G.remove_nodes_from(nodelist)
  return G

def internal_nets(G):
  """Return a list of internal nets in a networkx DiGraph created by
  verilog2networkx, as identified by the shapes "diamond" and "point"

  Keyword arguments:
  G -- a networkx DiGraph created by verilog2networkx

  Example:
  >>> G = verilog2networkx('counter.v')
  >>> internal_nets(G)
  ['n7', 'n14', 'n12', 'n2', 'n3', 'n13', 'n23', 'n5']
  """
  return [x for x in G.nodes if 'shape' in G.node[x] and G.node[x]['shape'] in ('diamond','point')]

def remove_internal_nets(G):
  """Remove internal nets from a networkx DiGraph created by verilog2networkx,
  without removing the connecting edges, and return the resulting DiGraph.

  Keyword arguments:
  G -- a networkx DiGraph created by verilog2networkx

  Example:
  >>> G = verilog2networkx('counter.v')
  >>> list(G.predecessors('n5'))
  ['c39']
  >>> list(G.successors('n5'))
  ['c43', 'c53']
  >>> newG = remove_internal_nets(G)
  >>> list(newG.predecessors('c43'))
  ['c39', 'c42']
  >>> list(newG.successors('c39'))
  ['c53', 'c43']
  """

  # nodes with diamond or point shapes are internal nets
  remove = internal_nets(G)
  G = remove_nodes(G, remove)
  return G

def main(argv):
  def usage():
    print("yosys_networkx.py [-s] <filename1> <filename2> ...")
    print("  filename1 filename2 ... : list of Verilog files to convert")
    print("  -s : synthesize using ABC (default: don't synthesize)")
    sys.exit(2)

  import getopt
  try:
    opts, args = getopt.getopt(argv,"s")
  except getopt.GetoptError:
    usage()
  if len(args)==0:
    usage()

  synthesize = False
  for opt, arg in opts:
    if opt == "-s":
      synthesize = True

  for filename in args:
    prefix = filename.replace('.v','')
    G = verilog2networkx(filename, synthesize=synthesize, pngfile=prefix+".png", dotfile=prefix+".dot")
    G = remove_internal_nets(G)
    with open(prefix+".edges", "w") as f:
      f.write(str(list(G.edges())))

if __name__ == "__main__":
  import sys
  main(sys.argv[1:])

