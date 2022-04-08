from pikachu.reactions.basic_reactions import condensation, hydrolysis
from pikachu.reactions.functional_groups import find_bonds, BondDefiner, GroupDefiner, find_atoms
from class_domain import ATTRIBUTES


THIOESTERBOND = BondDefiner('thioester_bond', 'SC(C)=O', 0, 1)
THIOESTER_CARBON = GroupDefiner('thioester carbon', 'SC(C)=O', 1)
LEAVING_OH_BOND = BondDefiner('Leaving -OH group bond', 'C(=O)(O)CN', 0, 2)
N_AMINO_ACID = GroupDefiner('Nitrogen atom amino acid', 'NCC(=O)O', 0)
C1_AMINO_ACID = GroupDefiner('C1 atom amino acid', 'NCC(=O)O', 1)
C2_AMINO_ACID = GroupDefiner('C2 atom amino acid', 'NCC(=O)O', 2)


def set_nrps_central_chain(peptide):
    n_atoms_aa = find_atoms(N_AMINO_ACID, peptide)
    c1_atoms_aa = find_atoms(C1_AMINO_ACID, peptide)
    c2_atoms_aa = find_atoms(C2_AMINO_ACID, peptide)

    assert len(n_atoms_aa) == 1
    assert len(c1_atoms_aa) == 1
    assert len(c2_atoms_aa) == 1

    n_atoms_aa[0].annotations.in_central_chain = True
    c1_atoms_aa[0].annotations.in_central_chain = True
    c2_atoms_aa[0].annotations.in_central_chain = True


def condensation_nrps(amino_acid, nrp_intermediate):
    """
    Returns the NRPS condensation product as a PIKAChU Structure object

    amino_acid: PIKAChU Structure object of the amino acid
    nrp_intermediate: PIKAChU Structure object of the NRP intermediate
    """
    # Initialize annotations in all atoms in amino acid
    for atom in amino_acid.graph:
        if not hasattr(atom.annotations, 'in_central_chain'):

            for attribute in ATTRIBUTES:
                atom.annotations.add_annotation(attribute, False)

    # If this is the first elongation reaction, determine central peptide
    if not any(atom.annotations.in_central_chain for atom in nrp_intermediate.graph):
        set_nrps_central_chain(nrp_intermediate)

    # Check if the intermediate is a thioester intermediate, if so: convert
    is_thioester = False
    found_bonds_thioester = find_bonds(THIOESTERBOND, nrp_intermediate)
    oh_bond = None

    if len(found_bonds_thioester) > 0:
        is_thioester = True
        nrp_intermediate, oh_bond = sulphur_to_hydroxyl(nrp_intermediate)
        # for atom in nrp_intermediate.graph:
        #     if not hasattr(atom.annotations, 'in_central_chain'):
        #
        #         for attribute in ATTRIBUTES:
        #             atom.annotations.add_annotation(attribute, False)

    # Define reaction targets

    if not is_thioester:
        found_bonds = find_bonds(LEAVING_OH_BOND, nrp_intermediate)
        assert len(found_bonds) == 1
        oh_bond = found_bonds[0]

    assert oh_bond

    # If the amino acid unit contains an unknown moiety, add a number to the
    # '*' atom to display in the structure drawing
    pk_chain_atom_types = []
    for atom in nrp_intermediate.graph:
        pk_chain_atom_types.append(atom.type)
    nr_unknown_atoms = pk_chain_atom_types.count('*')
    for atom in amino_acid.graph:
        if atom.type == '*':
            atom.unknown_index = nr_unknown_atoms + 1

    # Define the bond attached to the -H leaving group
    n_atoms_aa = find_atoms(N_AMINO_ACID, amino_acid)
    assert len(n_atoms_aa) == 1
    n_atom = n_atoms_aa[0]

    h_bond = None

    for bond in n_atom.bonds:
        for neighbour in bond.neighbours:
            if neighbour.type == 'H':
                h_bond = bond
                break

    assert h_bond

    # Determine atoms in amino acid that end up in central peptide chain
    set_nrps_central_chain(amino_acid)

    # Carry out condensation reaction using build-in PIKAChU function

    condensation_product = condensation(nrp_intermediate, amino_acid, oh_bond, h_bond)[0]

    # Refresh condensation product
    condensation_product.refresh_structure(find_cycles=True)

    # Initialize annotations for atoms that don't have any yet
    for atom in condensation_product.graph:
        if not hasattr(atom.annotations, 'in_central_chain'):
            for attribute in ATTRIBUTES:
                atom.annotations.add_annotation(attribute, False)

    return condensation_product


def sulphur_to_hydroxyl(thioester_structure):
    """
    Identifies and removes the sulphur (and attached atoms/domains) in the
    thioester structure and replaces it with a hydroxyl group, creating a
    carboxylic acid group. Returns the product of this reaction, also as a
    PIKAChU Structure object.

    thioester_structure: PIKAChU Structure object of a thioester (R-C(S)=O)
    """
    # Find thioester bond in the input structure
    found_bonds_thioester = find_bonds(THIOESTERBOND, thioester_structure)
    found_carbon_thioester = find_atoms(THIOESTER_CARBON, thioester_structure)

    assert len(found_carbon_thioester)
    assert len(found_bonds_thioester) == 1

    carbon_thioester = found_carbon_thioester[0]
    sh_bond = found_bonds_thioester[0]

    structures = hydrolysis(thioester_structure, sh_bond)
    combined = None
    for structure in structures:
        if carbon_thioester in structure.graph:
            combined = structure
            break

    assert combined

    oxygens = carbon_thioester.get_neighbours('O')

    oxygen_hydroxyl = None

    for oxygen in oxygens:
        if oxygen.get_bond(carbon_thioester).type == 'single' and oxygen.has_neighbour('H'):
            oxygen_hydroxyl = oxygen
            break

    assert oxygen_hydroxyl

    oh_bond = combined.bond_lookup[oxygen_hydroxyl][carbon_thioester]

    for atom in combined.graph:
        if not hasattr(atom.annotations, 'in_central_chain'):
            for attribute in ATTRIBUTES:
                atom.annotations.add_annotation(attribute, False)

    return combined, oh_bond
