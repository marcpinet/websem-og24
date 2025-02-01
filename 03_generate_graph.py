import rdflib
from rdflib import Graph, URIRef
from pyvis.network import Network
import networkx as nx
from tqdm import tqdm
import logging
import sys
import os
import webbrowser as wb


logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RDFVisualizer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.g = Graph()
        self.net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
        
        self.net.toggle_physics(True)
        self.net.barnes_hut(
            gravity=-2000,
            central_gravity=0.3,
            spring_length=200,
            spring_strength=0.05,
            damping=0.09,
            overlap=0
        )
        
    def load_graph(self):
        logger.info("Chargement du graphe RDF...")
        try:
            self.g.parse(self.file_path, format='turtle')
            logger.info(f"Nombre total de triplets chargés : {len(self.g)}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier : {e}")
            sys.exit(1)
    
    def calculate_graph_limits(self, max_nodes=500, max_edges=1000):
        unique_nodes = set()
        edges = set()
        
        logger.info("Analyse du graphe pour déterminer les limites...")
        for s, p, o in self.g:
            unique_nodes.add(str(s))
            unique_nodes.add(str(o))
            edges.add((str(s), str(o)))
        
        total_nodes = len(unique_nodes)
        total_edges = len(edges)
        
        density = total_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
            
        logger.info(f"Analyse du graphe terminée:")
        logger.info(f"Noeuds totaux dans le graphe: {total_nodes}")
        logger.info(f"Liens totaux dans le graphe: {total_edges}")
        logger.info(f"Densité du graphe: {density:.4f}")
        logger.info(f"Limites choisies par l'utilisateur - Max noeuds: {max_nodes}, Max liens: {max_edges}")
        
        return max_nodes, max_edges
    
    def create_visualization(self):
        max_nodes, max_edges = self.calculate_graph_limits()
        logger.info("Création de la visualisation...")
        
        node_connections = {}
        for s, _, o in self.g:
            node_connections[str(s)] = node_connections.get(str(s), 0) + 1
            node_connections[str(o)] = node_connections.get(str(o), 0) + 1
        
        sorted_nodes = sorted(node_connections.items(), key=lambda x: x[1], reverse=True)
        selected_nodes = set(node for node, _ in sorted_nodes[:max_nodes])
        
        with tqdm(total=len(selected_nodes), desc="Ajout des nœuds") as pbar:
            for node in selected_nodes:
                label = self._get_label(URIRef(node))
                self.net.add_node(node, label=label, title=node)
                pbar.update(1)
        
        added_edges = set()
        edge_count = 0
        with tqdm(total=max_edges, desc="Ajout des liens") as pbar:
            for s, p, o in self.g:
                if edge_count >= max_edges:
                    break
                    
                s_str, o_str = str(s), str(o)
                if s_str in selected_nodes and o_str in selected_nodes:
                    edge_key = (s_str, o_str)
                    if edge_key not in added_edges:
                        self.net.add_edge(s_str, o_str, title=self._get_label(p))
                        added_edges.add(edge_key)
                        edge_count += 1
                        pbar.update(1)
        
        logger.info(f"Visualisation créée avec {len(selected_nodes)} nœuds et {edge_count} liens")
    
    def _get_label(self, uri):
        if isinstance(uri, URIRef):
            label = uri.split('/')[-1].split('#')[-1]
            return label[:30] + '...' if len(label) > 30 else label
        return str(uri)
    
    def save_visualization(self, output_file="rdf_graph.html"):
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            self.net.save_graph(output_file)
            logger.info(f"Visualisation sauvegardée dans {output_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde : {e}")


def main():
    file_path = "og24_data_enriched_and_linked.ttl"
    visualizer = RDFVisualizer(file_path)
    
    try:
        visualizer.load_graph()
        visualizer.create_visualization()
        output_dir = "./"
        output_file = os.path.join(output_dir, "generated_graph.html")
        visualizer.save_visualization(output_file)
        logger.info("Ouverture de la visualisation dans le navigateur...")
        file_path = os.path.abspath(output_file)
        wb.open_new_tab("file://" + file_path)
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()