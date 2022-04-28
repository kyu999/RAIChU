from raichu.visualize_cluster import *
from pikachu.general import draw_structure, structure_to_smiles, draw_smiles


clust = [['module 1', 'starter_module_pks', 'SC(=O)CC'],
         ['module 2', 'elongation_module_pks', 'pk', []],
         ['module 3', 'elongation_module_pks', 'pk', ['KR']],
         ['module 4', 'elongation_module_pks', 'pk', ['KR']],
         ['module 5', 'terminator_module_nrps', 'nrp', []]]

product = cluster_to_structure(clust, attach_to_acp=True)
lin_te = thioesterase_linear_product(product)
all_products = thioesterase_all_products(product)

RaichuDrawer(lin_te)
draw_structure(lin_te)