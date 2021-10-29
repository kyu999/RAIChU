from pks_elongation_reactions import *
from pikachu.general import *
from pk_attach_to_domain import *

RECENT_ELONGATION = BondDefiner('recent_elongation', 'O=CCC(=O)S', 0, 1)
RECENT_REDUCTION_COH = BondDefiner('recent_reduction_C-OH', 'OCCC(=O)S', 0, 1)
RECENT_REDUCTION_CC = BondDefiner('recent_reduction_C-C', 'OCCC(=O)S', 1, 2)
RECENT_DEHYDRATION = BondDefiner('recent_dehydration', 'SC(C=CC)=O', 2, 3)


def carbonyl_to_hydroxyl(double_bond):
    """Alters the double bond in a carbonyl group to a single bond

    double_bond: Bond object of the bond between the C and O atom of a carbonyl
    group
    """
    #Assert the correct bond is parsed
    assert double_bond.type == 'double'
    atom_types_in_bond = []
    for atom in double_bond.neighbours:
        atom_types_in_bond.append(atom.type)
    assert 'O' in atom_types_in_bond and 'C' in atom_types_in_bond

    # Define the two electrons in the pi bond (inside the db) that needs
    # to be broken
    electrons_in_db = double_bond.electrons
    for electron in electrons_in_db:
        if electron.atom.type == 'O' and electron.orbital_type == 'p':
            electron_1 = electron
        elif electron.atom.type == 'C' and electron.orbital_type == 'p':
            electron_2 = electron

    #Remove the pi electrons from their respective orbital
    orbital_1 = electron_1.orbital
    orbital_2 = electron_2.orbital
    orbital_1.remove_electron(electron_2)
    orbital_2.remove_electron(electron_1)

    #Set bond type to single
    for bond in double_bond.atom_1.bonds:
        if bond == double_bond:
            bond.type = 'single'
    for bond in double_bond.atom_2.bonds:
        if bond == double_bond:
            bond.type = 'single'

    #Remove pi electrons from the Bond between the C and O atom
    for electron in double_bond.electrons[:]:
        if electron == electron_1 or electron == electron_2:
            double_bond.electrons.remove(electron)

    #Change hybridisation of both C and O atoms to sp3
    atom_1, atom_2 = double_bond.neighbours
    atom_1.valence_shell.dehybridise()
    atom_1.valence_shell.hybridise('sp3')
    atom_2.valence_shell.dehybridise()
    atom_2.valence_shell.hybridise('sp3')

    #Change bond_type of Bond instance to single
    double_bond.type = 'single'

    new_single_bond = double_bond
    new_single_bond.set_bond_summary()
    return new_single_bond



def find_betaketon(structure):
    """
    Returns the bond between the carbonyl oxygen and -carbon of the beta ketone
    group

    structure: Structure object
    """
    locations = structure.find_substructures(RECENT_ELONGATION.structure)
    bonds = []
    for match in locations:
        atom_1 = match.atoms[RECENT_ELONGATION.atom_1]
        atom_2 = match.atoms[RECENT_ELONGATION.atom_2]
        bond = structure.bond_lookup[atom_1][atom_2]
        bonds.append(bond)
    return bonds

def ketoreductase(chain_intermediate):
    """
    Performs the ketoreductase reaction on the PKS chain intermediate, returns
    the reaction product as a Structure object

    chain_intermediate: Structure object of a PKS chain intermediate just
    after an elongation step using (methyl)malonyl-CoA
    """
    #Reset all colours to black:
    for atom in chain_intermediate.graph:
        atom.draw.colour = 'black'
    for bond_nr, bond in chain_intermediate.bonds.items():
        bond.set_bond_summary()

    #Identify beta-ketone bond, identify O- and C-atom participating in bond
    beta_ketone_bond = find_betaketon(chain_intermediate)
    for bond in beta_ketone_bond:
        for atom in bond.neighbours:
            if atom.type == 'O':
                carbonyl_oxygen = atom
            elif atom.type == 'C':
                carbonyl_carbon = atom
            else:
                raise Exception('Cannot find atoms in beta ketone bond')

    #Change carbonyl bond to single bond
    for bond in beta_ketone_bond:
        new_single_bond = carbonyl_to_hydroxyl(bond)


    #Add H atom to form hydroxyl group and another H to the C
    chain_intermediate.add_atom('H', [carbonyl_oxygen])
    chain_intermediate.add_atom('H', [carbonyl_carbon])
    carbonyl_carbon.chiral = 'counterclockwise'

    #Set bond summary for newly formed bond (cannot do from struct.bonds?)
    for atom in chain_intermediate.graph:
        if atom == carbonyl_carbon:
            for bond in atom.bonds:
                for neighbour in bond.neighbours:
                    if neighbour.type == 'O':
                        the_bond = bond
    the_bond.set_bond_summary()

    # Refresh structure :)
    chain_intermediate.set_atom_neighbours()
    chain_intermediate.find_cycles()
    for atom in chain_intermediate.graph:
        atom.set_connectivity()
    for bond_nr, bond in chain_intermediate.bonds.items():
        bond.set_bond_summary()

    #Add colouring to the tailored group
    for atom in new_single_bond.neighbours:
        atom.draw.colour = 'red'


    return chain_intermediate

def dehydratase(chain_intermediate):
    """
    Performs the dehydratase reaction on the PKS chain intermediate, returns
    the reaction product as a Structure object

    chain_intermediate: Structure object of a PKS chain intermediate where the
    beta ketone group has been recently reduced by the KR domain
    """
    #Reset atom colours to black
    for atom in chain_intermediate.graph:
        atom.draw.colour = 'black'
    for bond_nr, bond in chain_intermediate.bonds.items():
        bond.set_bond_summary()

    #Find and define the atoms that participate in the bond changes
    co_bond = find_oh_dh(chain_intermediate)
    for bond in co_bond[:]:
        for neighbour in bond.neighbours:
            if neighbour.type == 'C':
                c2 = neighbour
            elif neighbour.type == 'O':
                o_oh = neighbour
    cc_bond = find_cc_dh(chain_intermediate)
    for bond in cc_bond[:]:
        bond.type = 'double'
        for neighbour in bond.neighbours:
            if neighbour == c2:
                pass
            else:
                c1 = neighbour

    #Remove hydroxyl group from c2
    for bond in co_bond[:]:
        chain_intermediate.break_bond(bond)
    split = chain_intermediate.split_disconnected_structures()
    chain_intermediate, oh = split

    #Remove proton from c1
    for atom in chain_intermediate.graph:
        if atom == c1:
            for neighbour in atom.neighbours:
                if neighbour.type == 'H':
                    for bond in neighbour.bonds:
                        bond_to_break = bond
                    break
    chain_intermediate.break_bond(bond_to_break)
    split = chain_intermediate.split_disconnected_structures()
    for structure in split:
        if len(structure.graph) == 1:
            proton = structure
        else:
            chain_intermediate = structure

    # Patch. When the bond is broken, the electron is not removed from
    # the orbitals of the C atom.
    for atom in chain_intermediate.graph:
        if atom == c1:
            c1 = atom

    #Make double c1=c2 bond
    form_double_bond(c1, c2)

    #After double bond formation, remove chirality c1 and c2
    for atom in chain_intermediate.graph:
        if atom == c1:
            atom.chiral = None
        elif atom == c2:
            atom.chiral = None
    for orbital_name in c1.valence_shell.orbitals:
        orbital = c1.valence_shell.orbitals[orbital_name]

    #add colouring
    for atom in chain_intermediate.graph:
        if atom == c1:
            for bond in atom.bonds:
                for neighbour in bond.neighbours:
                    if neighbour == c2:
                        the_bond = bond
    for atom in the_bond.neighbours:
        atom.draw.colour = 'blue'
    for atom in chain_intermediate.graph:
        if atom == c2:
            for bond in atom.bonds:
                for neighbour in bond.neighbours:
                    if neighbour == c1:
                        the_bond = bond
    for atom in the_bond.neighbours:
        atom.draw.colour = 'blue'

    #Refresh structure :)
    for atom in chain_intermediate.graph:
        atom.get_connectivity()
    chain_intermediate.set_atom_neighbours()
    chain_intermediate.set_connectivities()
    chain_intermediate.find_cycles()
    for bond_nr, bond in chain_intermediate.bonds.items():
        bond.set_bond_summary()


    return chain_intermediate


def form_double_bond(atom1, atom2):
    """Forms a double bond between two carbon atoms which are already single
    bonded

    atom1: Atom object of a carbon atom bonded with atom2 through a single bond
    atom2: Atom object of a carbon atom bonded with atom1 through a single bond
    """
    #Select the bonding electron in the first atom valence shell
    for orbital_name in atom2.valence_shell.orbitals:
        orbital = atom2.valence_shell.orbitals[orbital_name]
        if len(orbital.electrons) == 1:
            orbital_2 = orbital
            electron_2 = orbital.electrons[0]
    for orbital_name in atom1.valence_shell.orbitals:
        orbital = atom1.valence_shell.orbitals[orbital_name]
        if len(orbital.electrons) == 1:
            orbital_1 = orbital
            electron_1 = orbital.electrons[0]

    #Add the lone electron of atom 1 to the orbital of atom 2 and vice versa
    orbital_1.add_electron(electron_2)
    orbital_2.add_electron(electron_1)

    #Change hybridisation
    atom1.valence_shell.dehybridise()
    atom1.valence_shell.hybridise('sp2')
    atom2.valence_shell.dehybridise()
    atom2.valence_shell.hybridise('sp2')
    print('valence shell atom c2')
    atom2.valence_shell.print_shell()
    print(orbital_1, 'ORBITAL 1')

    #Make sure that the electrons of the new bond are in type p orbitals instead of sp2
    if not orbital_1.orbital_type == 'p':
        electrons_in_sp2 = orbital_1.electrons
        print('electrons in sp2', electrons_in_sp2)
        for orbital_name in atom1.valence_shell.orbitals:
            orbital = atom1.valence_shell.orbitals[orbital_name]
            if orbital.orbital_type == 'p':
                p_orbital_1 = orbital
                electrons_in_p = orbital.electrons
    if not orbital_2.orbital_type == 'p':
        electrons_in_sp2_2 = orbital_1.electrons
        for orbital_name in atom2.valence_shell.orbitals:
            orbital = atom2.valence_shell.orbitals[orbital_name]
            if orbital.orbital_type == 'p':
                p_orbital_2 = orbital
                electrons_in_p_2 = orbital.electrons

    #swap electrons in sp and p orbitals if not correct yet
    if not orbital_1.orbital_type == 'p':
        orbital_1.electrons = electrons_in_p
        p_orbital_1.electrons = electrons_in_sp2
    if not orbital_2.orbital_type == 'p':
        orbital_2.electrons = electrons_in_p_2
        p_orbital_2.electrons = electrons_in_sp2_2

    #Set right orbital name for all electrons in all orbitals
    for orbital_name in atom1.valence_shell.orbitals:
        orbital = atom1.valence_shell.orbitals[orbital_name]
        for electron in orbital.electrons:
            if atom1.valence_shell.atom == electron.atom:
                electron.set_orbital(orbital)
    for orbital_name in atom2.valence_shell.orbitals:
        orbital = atom2.valence_shell.orbitals[orbital_name]
        for electron in orbital.electrons:
            if atom2.valence_shell.atom == electron.atom:
                electron.set_orbital(orbital)

    #Add the new electrons of the pi-bond to the Bond between the two atoms
    for bond in atom1.bonds:
        for neighbour in bond.neighbours:
            if neighbour == atom2:
                newly_double_bond = bond
    for orbital_name in atom1.valence_shell.orbitals:
        orbital = atom1.valence_shell.orbitals[orbital_name]
        if orbital.orbital_type == 'p':
            for electron in orbital.electrons:
                if electron not in newly_double_bond.electrons:
                    newly_double_bond.electrons.append(electron)
    for orbital_name in atom2.valence_shell.orbitals:
        orbital = atom2.valence_shell.orbitals[orbital_name]
        if orbital.orbital_type == 'p':
            for electron in orbital.electrons:
                if electron not in newly_double_bond.electrons:
                    newly_double_bond.electrons.append(electron)

def find_oh_dh(structure):
    """
    Returns the Bond between the C and OH group to carry out the DH reaction

    structure: Structure object
    """
    locations = structure.find_substructures(RECENT_REDUCTION_COH.structure)
    structure.refresh_structure()
    structure.get_connectivities()
    structure.set_atom_neighbours()
    bonds = []
    for match in locations:
        atom_1 = match.atoms[RECENT_REDUCTION_COH.atom_1]
        atom_2 = match.atoms[RECENT_REDUCTION_COH.atom_2]
        bond = structure.bond_lookup[atom_1][atom_2]
        bonds.append(bond)
    return bonds


def find_cc_dh(structure):
    """
    Returns the Bond between the two C's that needs to be doubled

    structure: Structure object
    """
    locations = structure.find_substructures(RECENT_REDUCTION_CC.structure)
    bonds = []
    for match in locations:
        atom_1 = match.atoms[RECENT_REDUCTION_CC.atom_1]
        atom_2 = match.atoms[RECENT_REDUCTION_CC.atom_2]
        bond = structure.bond_lookup[atom_1][atom_2]
        bonds.append(bond)
    return bonds

def enoylreductase(chain_intermediate):
    """
    Performs the enoylreductase reaction on the PKS chain intermediate, returns
    the reaction product as a Structure object

    chain_intermediate: Structure object of a PKS chain intermediate where the
    beta ketone group has been recently reduced and dehydrated by the KR and
    ER domains, respectively
    """
    # reset all colours to black:
    for atom in chain_intermediate.graph:
        atom.draw.colour = 'black'
    chain_intermediate.set_atom_neighbours()
    for atom in chain_intermediate.graph:
        atom.set_connectivity()

    #Find double bond, change to single bond
    double_cc_bond = find_double_cc(chain_intermediate)
    atoms_in_double_bond = []
    for bond in double_cc_bond:
        atom_1 = bond.neighbours[0]
        atom_2 = bond.neighbours[1]
        atoms_in_double_bond.append(atom_1)
        atoms_in_double_bond.append(atom_2)
        double_to_single(bond, chain_intermediate)

    #Add H-atom to the C atoms participating in the new single bond
    for neighbour in bond.neighbours:
        chain_intermediate.add_atom('H', [neighbour])

    # Return chirality C atom in the case that the previous elongation reaction
    # was performed using methylmalonyl-CoA
    for atom in atoms_in_double_bond:
        carbon_neighbours = 0
        for neighbour in atom.neighbours:
            if neighbour.type == 'C':
                carbon_neighbours += 1
        if carbon_neighbours == 3:
            atom.chiral = 'clockwise'


    # add colouring to highlight tailoring reaction
    for atom in chain_intermediate.graph:
        if atom == atom_1:
            for bond in atom.bonds:
                for neighbour in bond.neighbours:
                    if neighbour == atom_2:
                        the_bond = bond
    for atom in the_bond.neighbours:
        atom.draw.colour = 'LIME'
    for atom in chain_intermediate.graph:
        if atom == atom_2:
            for bond in atom.bonds:
                for neighbour in bond.neighbours:
                    if neighbour == atom_1:
                        the_bond = bond
    for atom in the_bond.neighbours:
        atom.draw.colour = 'LIME'


    return chain_intermediate


def find_double_cc(structure):
    """
    Returns the double Bond between the two C's that needs to be reduced

    structure: Structure object
    """
    locations = structure.find_substructures(RECENT_DEHYDRATION.structure)
    bonds = []
    for match in locations:
        atom_1 = match.atoms[RECENT_DEHYDRATION.atom_1]
        atom_2 = match.atoms[RECENT_DEHYDRATION.atom_2]
        bond = structure.bond_lookup[atom_1][atom_2]
        bonds.append(bond)
    return bonds


def double_to_single(double_bond, structure):
    """Alters the double bond in a carbonyl group to a single bond

    double_bond
    """
    assert double_bond.type == 'double'
    c1 = double_bond.atom_1
    c2 = double_bond.atom_2

    #Define the electrons in the pi bond that need to be removed
    pi_electrons = []
    for electron in double_bond.electrons:
        if electron.orbital_type == 'p':
            pi_electrons.append(electron)

    #Remove electrons that participate in the pi bond from each atom in the bond
    for orbital_name in c1.valence_shell.orbitals:
        orbital = c1.valence_shell.orbitals[orbital_name]
        for electron in orbital.electrons:
            if electron in pi_electrons:
                orbital.remove_electron(electron)
    for orbital_name in c2.valence_shell.orbitals:
        orbital = c2.valence_shell.orbitals[orbital_name]
        for electron in orbital.electrons:
            if electron in pi_electrons:
                orbital.remove_electron(electron)

    #Change hybridisation from sp2 to sp3
    c1.valence_shell.dehybridise()
    c1.valence_shell.hybridise('sp3')
    c2.valence_shell.dehybridise()
    c2.valence_shell.hybridise('sp3')

    #Remove pi electrons from bond
    for electron in double_bond.electrons[:]:
        print(electron, electron.orbital_type)
        if electron.orbital_type == 'p':
            double_bond.electrons.remove(electron)

    #Change bondtype to single
    double_bond.type = 'single'



if __name__ == "__main__":
    some_example = Smiles('SC(=O)CC(=O)CCCCC').smiles_to_structure()
    #Drawer(some_example)

    #Reduce beta-ketone group to -OH (perform reaction KR domain)
    new_chain = ketoreductase(some_example)
    #Drawer(new_chain)

    #Perform reaction DH domain (removal water, make double bond)
    new_chain2 = dehydratase(new_chain)
    #Drawer(new_chain2)

    #perform reaction ER domain (reduce newly formed C=C to C-C)
    new_chain3 = enoylreductase(new_chain2)
    #Drawer(new_chain3)

    #Attach to ACP domain
    new_chain4 = attach_to_domain(new_chain3, 'ACP')
    #Drawer(new_chain4)



    new_chain5 = add_methylmalonylunit(new_chain4)
    Drawer(new_chain5)