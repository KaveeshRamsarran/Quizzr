"""
Builds five sample lecture PDFs in samples/lectures/ for trying Quizzr and for
testing the built-in card generator. Each one is a different style of notes:

  1. Biology notes       - prose with definitions
  2. History lecture     - people, dates and inventions
  3. CS slides           - one topic per page, "Term: definition" fragments
  4. Economics textbook  - long paragraphs, definitions mid-paragraph
  5. Physics lecture     - laws, formulas, units and numbered steps

No third-party libraries: the PDFs are written by hand (Helvetica, WinAnsi).
Run:  python samples/make_lectures.py
"""

from __future__ import annotations

import os
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lectures")

# A page is a list of blocks: ("title"|"h"|"p"|"b"|"n"|"gap", text)
LECTURES = {
    "bio201-genetics-and-inheritance.pdf": ("BIO 201 Genetics, Lecture 7", [
        [
            ("title", "Genetics and Inheritance"),
            ("p", "These notes cover how traits are passed from parents to offspring, the structure of genes, "
                  "and the experiments that founded modern genetics."),
            ("h", "DNA and Genes"),
            ("p", "DNA (deoxyribonucleic acid) is the molecule that carries genetic instructions in all living organisms. "
                  "A gene is a segment of DNA that codes for a specific protein. Genes are located on chromosomes, "
                  "which are long strands of DNA wrapped around proteins called histones."),
            ("p", "Humans have 23 pairs of chromosomes, for a total of 46. One chromosome of each pair is inherited from "
                  "each parent."),
            ("h", "Alleles"),
            ("p", "An allele is a variant form of a gene. A dominant allele is expressed even when only one copy is present. "
                  "A recessive allele is only expressed when two copies are present."),
            ("p", "An organism with two identical alleles for a trait is homozygous, while an organism with two different "
                  "alleles is heterozygous. The genotype is the genetic makeup of an organism, whereas the phenotype is its "
                  "set of observable characteristics."),
        ],
        [
            ("h", "Mendel's Laws"),
            ("p", "Gregor Mendel is known as the father of modern genetics. Mendel performed his experiments on pea plants "
                  "in the 1850s and 1860s."),
            ("p", "The law of segregation states that the two alleles for a trait separate during the formation of gametes. "
                  "The law of independent assortment states that genes for different traits are inherited independently of "
                  "each other."),
            ("p", "A Punnett square is a diagram used to predict the outcome of a genetic cross. A cross between two "
                  "heterozygous parents produces a 3:1 ratio of dominant to recessive phenotypes."),
            ("h", "Mutations"),
            ("p", "A mutation is a permanent change in the DNA sequence. Mutagens are agents, such as ultraviolet light and "
                  "certain chemicals, that increase the rate of mutation."),
            ("p", "Types of mutation:"),
            ("b", "Point mutation: a change in a single nucleotide"),
            ("b", "Insertion: one or more nucleotides are added to the sequence"),
            ("b", "Deletion: one or more nucleotides are removed from the sequence"),
            ("b", "Frameshift mutation: an insertion or deletion that shifts the reading frame"),
        ],
        [
            ("h", "Meiosis"),
            ("p", "Meiosis is a type of cell division that produces four genetically different haploid cells. Gametes are "
                  "haploid, meaning they contain one set of chromosomes."),
            ("p", "Crossing over occurs during prophase I, when homologous chromosomes exchange segments of DNA. Crossing "
                  "over increases genetic variation in the offspring."),
            ("p", "Mitosis, by contrast, produces two genetically identical diploid cells and is used for growth and repair."),
        ],
    ]),

    "hist110-industrial-revolution.pdf": ("HIST 110 Modern Europe, Lecture 4", [
        [
            ("title", "The Industrial Revolution"),
            ("h", "Origins"),
            ("p", "The Industrial Revolution began in Britain in the late 18th century. Britain had large reserves of coal "
                  "and iron ore, which fuelled early industry. The enclosure movement pushed many rural workers into cities, "
                  "creating a large labour force."),
            ("p", "Britain also had a stable government, a growing empire that supplied raw materials, and banks willing to "
                  "lend money to new businesses."),
            ("h", "Key Inventions"),
            ("p", "In 1764, James Hargreaves invented the spinning jenny, which allowed one worker to spin several threads at "
                  "once. James Watt improved the steam engine in 1769 by adding a separate condenser."),
            ("p", "The power loom, patented by Edmund Cartwright in 1785, mechanised weaving. George Stephenson built the "
                  "Rocket, an early steam locomotive, in 1829."),
        ],
        [
            ("h", "The Factory System"),
            ("p", "The factory system brought workers and machines together under one roof. Child labour was common in early "
                  "textile mills, where children as young as six worked long shifts."),
            ("p", "The Factory Act of 1833 limited the working hours of children in textile factories and introduced "
                  "factory inspectors."),
            ("h", "Urbanisation"),
            ("p", "Urbanisation is the growth of towns and cities as people move from rural areas. Manchester grew from a "
                  "market town into the centre of the cotton industry. Poor sanitation in crowded cities led to outbreaks "
                  "of cholera."),
            ("h", "Social Change"),
            ("p", "The working class emerged as a new social group of wage labourers. Luddites were textile workers who "
                  "destroyed machinery in protest between 1811 and 1816."),
            ("p", "Trade unions are organisations of workers that bargain collectively for better wages and conditions. The "
                  "Combination Acts of 1799 and 1800 made trade unions illegal in Britain; they were repealed in 1824."),
        ],
    ]),

    "cs220-data-structures-slides.pdf": ("CS 220 Data Structures, Week 9 slides", [
        [
            ("title", "Core Data Structures"),
            ("p", "Big O notation describes how the running time of an algorithm grows as the input size grows."),
            ("h", "Arrays"),
            ("b", "Array: a collection of elements stored in contiguous memory"),
            ("b", "Access by index: O(1)"),
            ("b", "Insertion in the middle: O(n)"),
            ("b", "Fixed size in most languages"),
        ],
        [
            ("h", "Linked Lists"),
            ("b", "Linked list: a sequence of nodes where each node points to the next"),
            ("b", "Insertion at the head: O(1)"),
            ("b", "Search: O(n)"),
            ("b", "Doubly linked list: each node points to both the next and the previous node"),
        ],
        [
            ("h", "Stacks and Queues"),
            ("b", "Stack: a last-in, first-out (LIFO) collection"),
            ("b", "Queue: a first-in, first-out (FIFO) collection"),
            ("b", "Push adds an item to the top of a stack; pop removes the top item"),
            ("b", "Enqueue adds an item to the back of a queue; dequeue removes the front item"),
        ],
        [
            ("h", "Hash Tables"),
            ("b", "Hash table: maps keys to values using a hash function"),
            ("b", "Hash function: converts a key into an array index"),
            ("b", "Collision: two keys map to the same index"),
            ("b", "Chaining: stores colliding entries in a linked list at that index"),
            ("b", "Average lookup: O(1)"),
        ],
        [
            ("h", "Trees"),
            ("b", "Binary tree: a tree in which each node has at most two children"),
            ("b", "Binary search tree (BST): left subtree holds smaller keys, right subtree holds larger keys"),
            ("b", "Search in a balanced BST: O(log n)"),
            ("b", "Heap: a complete binary tree where each parent is ordered relative to its children"),
        ],
    ]),

    "econ101-supply-and-demand.pdf": ("ECON 101 Principles of Economics, Chapter 3", [
        [
            ("title", "Chapter 3: Supply and Demand"),
            ("p", "A market is a group of buyers and sellers of a particular good or service. The buyers as a group determine "
                  "the demand for the product, and the sellers as a group determine the supply of the product. In a "
                  "competitive market, there are so many buyers and sellers that each has a negligible impact on the market "
                  "price."),
            ("h", "Demand"),
            ("p", "The law of demand states that, other things equal, the quantity demanded of a good falls when the price of "
                  "the good rises. The demand curve is a graph of the relationship between the price of a good and the "
                  "quantity demanded. Because a lower price increases the quantity demanded, the demand curve slopes "
                  "downward."),
            ("p", "Income also affects demand. Normal goods are goods for which demand rises when income rises. Inferior goods "
                  "are goods for which demand falls when income rises; bus rides are a common example."),
            ("p", "Substitutes are pairs of goods for which an increase in the price of one leads to an increase in the demand "
                  "for the other. Complements are pairs of goods for which an increase in the price of one leads to a "
                  "decrease in the demand for the other."),
        ],
        [
            ("h", "Supply"),
            ("p", "The law of supply states that, other things equal, the quantity supplied of a good rises when the price of "
                  "the good rises. The supply curve slopes upward because a higher price makes production more profitable."),
            ("h", "Equilibrium"),
            ("p", "Equilibrium is a situation in which the market price has reached the level at which quantity supplied "
                  "equals quantity demanded. A surplus is a situation in which quantity supplied is greater than quantity "
                  "demanded. A shortage is a situation in which quantity demanded is greater than quantity supplied."),
            ("p", "When there is a surplus, sellers lower their prices, which moves the market toward equilibrium."),
            ("h", "Elasticity"),
            ("p", "Price elasticity of demand measures how much the quantity demanded responds to a change in price. Demand "
                  "is elastic when the elasticity is greater than 1 and inelastic when it is less than 1. Necessities tend "
                  "to have inelastic demand, while luxuries tend to have elastic demand."),
        ],
        [
            ("h", "Government Policies"),
            ("p", "A price ceiling is a legal maximum on the price at which a good can be sold. Rent control is a common "
                  "example of a price ceiling. A binding price ceiling causes a shortage."),
            ("p", "A price floor is a legal minimum on the price at which a good can be sold. The minimum wage is an example "
                  "of a price floor. A binding price floor causes a surplus."),
            ("p", "A tax on a good places a wedge between the price buyers pay and the price sellers receive. Tax incidence "
                  "is the manner in which the burden of a tax is shared among participants in a market."),
        ],
    ]),

    "phys101-newtons-laws.pdf": ("PHYS 101 Mechanics, Lecture 3", [
        [
            ("title", "Newton's Laws of Motion"),
            ("h", "The First Law"),
            ("p", "Newton's first law states that an object remains at rest or in uniform motion unless acted on by a net "
                  "force. Inertia is the tendency of an object to resist changes in its motion."),
            ("p", "Mass is a measure of the amount of matter in an object and is measured in kilograms."),
            ("h", "The Second Law"),
            ("p", "Newton's second law states that the net force on an object equals its mass times its acceleration "
                  "(F = ma). The SI unit of force is the newton (N), equal to one kilogram metre per second squared."),
            ("p", "Weight is the force of gravity acting on an object, calculated as W = mg. On Earth, the acceleration due "
                  "to gravity is approximately 9.8 m/s²."),
        ],
        [
            ("h", "The Third Law"),
            ("p", "Newton's third law states that for every action there is an equal and opposite reaction. When you push "
                  "on a wall, the wall pushes back on you with the same force."),
            ("h", "Friction"),
            ("p", "Friction is a force that opposes the relative motion of two surfaces in contact. Static friction acts on "
                  "objects at rest, while kinetic friction acts on moving objects."),
            ("h", "Momentum"),
            ("p", "Momentum is the product of an object's mass and velocity (p = mv). The law of conservation of momentum "
                  "states that the total momentum of a closed system remains constant."),
            ("h", "Solving Force Problems"),
            ("p", "Steps for solving a force problem:"),
            ("n", "1. Draw a free-body diagram showing every force on the object."),
            ("n", "2. Choose a coordinate system."),
            ("n", "3. Apply Newton's second law along each axis."),
            ("n", "4. Solve for the unknown quantity."),
            ("p", "Example: a 2 kg box pushed with a net force of 10 N accelerates at 5 m/s²."),
        ],
    ]),
}

STYLE = {  # font, size, leading, wrap width (characters)
    "title": ("F2", 20, 30, 50),
    "h": ("F2", 13.5, 22, 70),
    "p": ("F1", 11, 15.5, 92),
    "b": ("F1", 11, 15.5, 86),
    "n": ("F1", 11, 15.5, 86),
}


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(blocks, header: str, page_no: int, total: int) -> str:
    ops = ["BT"]
    ops.append(f"/F1 8.5 Tf 1 0 0 1 56 806 Tm ({esc(header)}) Tj")
    y = 768
    for kind, text in blocks:
        if kind == "gap":
            y -= 10
            continue
        font, size, leading, width = STYLE[kind]
        if kind == "h":
            y -= 8
        indent = 56
        prefix = ""
        if kind == "b":
            prefix, indent = "• ", 68
        lines = textwrap.wrap(text, width) or [""]
        for i, line in enumerate(lines):
            x = indent if (i == 0 or kind not in {"b", "n"}) else indent + 12
            shown = (prefix + line) if i == 0 else line
            ops.append(f"/{font} {size} Tf 1 0 0 1 {x} {y} Tm ({esc(shown)}) Tj")
            y -= leading
        y -= 5 if kind in {"p", "title"} else 1
    ops.append(f"/F1 8.5 Tf 1 0 0 1 280 30 Tm (Page {page_no} of {total}) Tj")
    ops.append("ET")
    return "\n".join(ops)


def write_pdf(path: str, header: str, pages) -> None:
    objs: list[str] = []

    def add(o: str) -> int:
        objs.append(o)
        return len(objs)

    f1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    pages_id = len(objs) + 2 * len(pages) + 1
    kids = []
    for n, blocks in enumerate(pages, 1):
        stream = page_stream(blocks, header, n, len(pages))
        data = stream.encode("cp1252")
        cid = add(f"<< /Length {len(data)} >>\nstream\n" + data.decode("latin-1") + "\nendstream")
        kids.append(add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Contents {cid} 0 R "
            f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> >>"
        ))
    assert add(f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>") == pages_id
    root = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {root} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as fh:
        fh.write(out)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for name, (header, pages) in LECTURES.items():
        path = os.path.join(OUT, name)
        write_pdf(path, header, pages)
        print(f"wrote {os.path.relpath(path, HERE)} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
