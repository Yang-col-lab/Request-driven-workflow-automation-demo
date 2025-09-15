import os
import re
import subprocess
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Gaussian")

path_default = "/data/corp/qun.zeng/mcp_tmp"
multiwfn_default = "/home/ssr/app/multiwfn/Multiwfn"

def parse_xyz_content(content):
    """
    This function interprets the content in the XYZ format strings to a list of atoms for Gaussian.
    It is designed for molecules, not for solids.
    
    parameters:
        content (str)  : content with XYZ format
    speed:
        very fast
    sence:
        Only for molecules
    returns:
        list: [(symbol, x, y, z), ...]
    """
    print(content)
    lines = content.strip().split('\n')
    atoms = []
    
    # Skip the first two lines (atom count and comment line)
    start_index = 0
    if len(lines) > 0 and lines[0].isdigit():
        start_index = 2
    
    for line in lines[start_index:]:
        if not line.strip():  # Skip empty lines
            continue
        parts = line.split()
        if len(parts) >= 4:  # Ensure atom symbol and XYZ coordinates exist
            try:
                atom_symbol = parts[0]
                coords = [float(x) for x in parts[1:4]]
                atoms.append((atom_symbol, coords))
            except ValueError:
                continue  # Skip malformed lines
    return atoms

@mcp.tool()
def xyz_to_gaussian_opt(xyz_string, jobname, method='b3lyp', basis='6-31g(d)', 
                         mem='2GB', nproc=4, charge=0, multiplicity=1, title="Molecular Optimization"):
    """
    This function generates a Gaussian input string for molecular optimization from XYZ format string.
    It is designed for molecules, not for solids.

    parameters:
        xyz_string (str)   : string of XYZ format
        jobname (str)      : job name for input files 
        method (str)       : method for the calcualtion (default: b3lyp)
        basis (str)        : basis set(default: 6-31g(d))
        mem (str)          : memory (default: 2GB)
        nproc (int)        : number of parallel cores (default: 4)
        charge (int)       : charge of the molecule (default: 0)
        multiplicity (int) : multiplicity (default: 1)
        title (str)        : task title (default: "Molecular Optimization")

    speed:
        very fast
    sence:
        Only for molecules
    returns:
        str: Gaussian input file string.The string contains line breaks("\n"). Do not perform any additional processing, to avoid calculation errors.
    """
    # Determine input type (file path or string)
    atoms = parse_xyz_content(xyz_string)
    if not atoms:
        raise ValueError("No valid atoms found in the provided XYZ content.")
    
    # Generate Gaussian input file
    input_string =  ""
    # 1. Resource settings
    input_string += f"%chk={jobname.strip()}.chk\n"
    input_string += f"%mem={mem}\n"
    input_string += f"%nprocshared={nproc}\n\n"
        
    # 2. Route section (calculation settings)
    input_string += f"# opt {method}/{basis}\n\n"
        
    # 3. Title line (avoid special characters)
    clean_title = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in title)
    input_string += f"{clean_title}\n\n"
        
    # 4. Charge and spin multiplicity
    input_string += f"{charge} {multiplicity}\n"
        
    # 5. Atomic coordinates (unit: Å)
    for atom_symbol, coords in atoms:
        x, y, z = coords
        input_string += f"{atom_symbol:>2} {x:>12.6f} {y:>12.6f} {z:>12.6f}\n"
        
    # 6. End with blank lines
    input_string +="\n\n\n"
    
    return input_string

@mcp.tool()
def gaussian_exec(input_string, filename, path=path_default, timeout=None):
    """
    This funciton executes Gaussian calculations in Linux, do not modify input_string.
    Parameters:
        input_string (str): Gaussian input string from xyz_to_gaussian_opt function. Must not perform any additional processing, to avoid calculation errors.
        filename (str): filename for Gaussain, suffix is ".gjf" or ".com"
        timeout (int): time-out period for Gaussian calculation, in seconds, default is None (no time-out)
    speed:
        very slow
    sence:
        Only for molecules
    Returns:
        int: A return code of zero indicates success, while any non-zero value indicates failure
    """
    try:
        #if filename[-4:] not in [".com", ".gjf"]: filename +=".com"
        print("input name", filename)
        print(input_string)
        if path[-1]!="/": path+="/"
        path_old = os.getcwd()
        os.chdir(path)
        # 1. Safely write file (avoid overwrite risk
        with open(filename, "w", encoding="utf-8") as f:
            f.write(input_string + "\n\n")
        
        # 2. Use subprocess instead of os.popen (safer and more efficient)
        cmd = ["g16", filename]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout  # avoid hanging
        )
        
        # 3. Error handling (log/raise)
        if result.returncode != 0:
            error_msg = f"Gaussian failed (Code: {result.returncode})\n Error:\n{result.stderr}"
            raise RuntimeError(error_msg)
        os.chdir(path_old)    
        return result.returncode
    
    except FileNotFoundError:
        raise RuntimeError("Can not found Gaussian 'g16'")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Gaussian time-out {timeout} seconds)")

@mcp.tool()
def extract_optimized_structure(filename, path=path_default):
    """
    The function extract_optimized_structure() reads a Gaussian log file and extracts the optimized structure, and returns the optimized structure or None if the optimization failed.
   
    parameters:
        filename (str): filename for Gaussain, suffix is ".gjf" or ".com"
    speed:
        very fast
    sence:
        only for molecule
    returns:
        list or None: list of optimized structure or None if the optimization failed
    """
    # Map from atomic number to element symbol
    atomic_num_to_symbol = {
        1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O',
        9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P',
        16: 'S', 17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca'
        # Extend with more elements as needed
    }
    
    try:
        if filename[-4:] not in [".com", ".gjf"]: filename +=".com"
        log_name = filename[:-4] + ".log"
        if path[-1]!="/": path += "/"
        print("log name", log_name)
        with open(path+log_name, 'r') as f:
            log_content = f.read()
        # Check whether optimization terminated normally [1,2](@ref)
        if "Normal termination" not in log_content:
            print("A")
            return None
        print("A+")
        
        if "Optimization completed." not in log_content:
            print("B")
            return None
        print("B+")

        # Locate the last optimized structure (Standard orientation) [1,2](@ref)
        
        log_lines = log_content.split("\n")
        iline = 0
        for i,line in enumerate(log_lines):
            if re.search("Optimization completed.", line):
                iline = i
                break
        for i,line in enumerate(log_lines[iline:]):
            if re.search("Standard orientation", line):
                iline += i
                break

        atoms = []
        for line in log_lines[iline+5:]:
            if re.search("-------", line):
                break
            tmp = line.split()
            symbol = int(tmp[1])
            x = float(tmp[-3])
            y = float(tmp[-2])
            z = float(tmp[-1])
            atoms.append([symbol, x, y, z])
        return atoms if atoms else None
    
    except Exception as e:
        print(f"Error: {e}")
        return None

@mcp.tool()
def formchk(chk_name, path=path_default):
    """
    The function formchk is used to convert chk file to fchk file
    Use the binary executable formchk to convert the $jobname.chkfile into the corresponding fchk file.    

    parameters:
        chk_name: file name of chk file
        path: chk file path
    speed:
        vary fast
    sence:
        only for molecule
        only for Gaussian
    returns:
        0 (Normal Exit) or None (Error Exit)
    """
    try:
        path_old = os.getcwd()
        os.chdir(path)
        cmd = ["formchk", chk_name]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1000  # avoid hanging
            )
        os.chdir(path_old)
        return 0
    except Exception as e:
        print("formchk process error: {e}")
        return None


@mcp.tool()
def extract_fchk_data(fchk_name, path=path_default):
    """
    The fucntiona is used to exect properties about energy, HOMO and LUMO from fchk file. 
    Only for closed-shell system.
    Parameters:
        fchk_name (str): The name of the file to check.
    speed:
        very fast
    sence:
        Only for molecules
    Returns:
        dict: A dictionary containing the properties of the file.
    """
    data = {"Energy": None, "HOMO": None, "LUMO": None}
    path_old = os.getcwd()
    os.chdir(path)
    with open(fchk_name, 'r') as f:
        lines = f.readlines()
    
    iline = 0
    for i, line in enumerate(lines):
        if "Total Energy" in line:
            data["Energy"] = float(line.split()[-1])  # Hartree
        if "Number of electrons" in line:
            data["Ne"] = int(line.split()[-1]) # 
        elif "Alpha Orbital Energies" in line:
            iline = i
            break

    nbasis = int(lines[iline].split()[-1])
    if nbasis % 5 == 0: 
        nline = nbasis//5
    else:
        nline = nbasis//5 + 1
    # Parse orbital energy list
    orb_energies = []
    for i in range(nline):
        orb_energies += list(map(float, lines[i+iline+1].split()))
    data["HOMO"] = orb_energies[data["Ne"]//2-1]
    data["LUMO"] = orb_energies[data["Ne"]//2]
    os.chdir(path_old)
    return data

def parse_multiwfn_surface_analysis(log_text):
    """
    The function is used to parse the output results of quantitative molecular surface analysis from multiwfn.
    Multiwfn is a binary executable file to analyze the gaussian output file.
    Parameters
    log_text : str
        The output results of multiwfn.
    Returns
    -------
    results : dict   
    """
    results = {
        "volume": {},          # properties about volume
        "density": None,       # density
        "esp_range": {},       # the range of ESP
        "surface_area": {},    # the statics of surface area
        "esp_stats": {},       # ESP statistical moments
        "polarity": {},        # Polarity partition
        "skewness": {},        # Skewness analysis
        "minima": None         # Coordinates of global minimum
    }
    
    # 1. Extract volume and density
    vol_match = re.search(r"Volume:\s+([\d.]+)\s+Bohr\^3\s+\(\s+([\d.]+)\s+Angstrom\^3\)", log_text)
    #vol = re.search(r"Volume:\s+(\S+)\s+Bohr\^3\s+\(\s+(\S+)\s+Angstrom\^3\)", log_text)
    if vol_match:
        results["volume"] = {
            "Bohr^3": float(vol_match.group(1)),
            "Angstrom^3": float(vol_match.group(2))
        }
    
    density_match = re.search(r"Estimated density.*?([\d.]+)\s+g/cm\^3", log_text)
    if density_match:
        results["density"] = float(density_match.group(1))
    
    # 2. Range of electrostatic potential (ESP)
    esp_min = re.search(r"Minimal value:\s+([\d.-]+)\s+kcal/mol", log_text)
    esp_max = re.search(r"Maximal value:\s+([\d.-]+)\s+kcal/mol", log_text)
    if esp_min and esp_max:
        results["esp_range"] = {
            "min_kcal/mol": float(esp_min.group(1)),
            "max_kcal/mol": float(esp_max.group(1))
        }
    
    # 3. Surface area statistics (with unit conversion)
    area_patterns = [
        ("total", r"Overall surface area:\s+(\S+)\s+Bohr\^2\s+\(\s+(\S+)\s+Angstrom\^2\)"),
        ("positive", r"Positive surface area:\s+([\d.]+)\s+Bohr\^2\s+\(\s+([\d.]+)\s+Angstrom\^2\)"),
        ("negative", r"Negative surface area:\s+([\d.]+)\s+Bohr\^2\s+\(\s+([\d.]+)\s+Angstrom\^2\)")
    ]
    for key, pattern in area_patterns:
        match = re.search(pattern, log_text)
        if match:
            results["surface_area"][key] = {
                "Bohr^2": float(match.group(1)),
                "Angstrom^2": float(match.group(2))
            }
    
    # 4. ESP statistical moments
    stats_patterns = {
        "overall_avg": r"Overall average value:\s+([\d.-]+)\s+a\.u\.",
        "positive_avg": r"Positive average value:\s+([\d.-]+)\s+a\.u\.",
        "negative_avg": r"Negative average value:\s+([\d.-]+)\s+a\.u\.",
        "total_variance": r"Overall variance.*?:\s+([\d.]+)\s+a\.u\.\^2",
        "positive_variance": r"Positive variance:\s+([\d.]+)\s+a\.u\.\^2",
        "negative_variance": r"Negative variance:\s+([\d.]+)\s+a\.u\.\^2",
        "charge_balance": r"Balance of charges \(nu\):\s+([\d.-]+)",
        "internal_separation": r"Internal charge separation \(Pi\):\s+([\d.-]+)\s+a\.u\.",
        "molecular_polarity": r"Molecular polarity index \(MPI\):\s+([\d.]+)\s+eV"
    }
    for key, pattern in stats_patterns.items():
        match = re.search(pattern, log_text)
        if match:
            results["esp_stats"][key] = float(match.group(1))
    
    # 5. Polarity partition
    polarity_match = re.search(
        r"Nonpolar surface area.*?([\d.]+)\s+Angstrom\^2\s+\(\s+([\d.]+)\s+\%\)\s+"
        r"Polar surface area.*?([\d.]+)\s+Angstrom\^2\s+\(\s+([\d.]+)\s+",
        log_text
    )
    if polarity_match:
        results["polarity"] = {
            "nonpolar_area": float(polarity_match.group(1)),
            "nonpolar_percent": float(polarity_match.group(2)),
            "polar_area": float(polarity_match.group(3)),
            "polar_percent": float(polarity_match.group(4))
        }
    
    # 6. Skewness analysis
    skew_patterns = {
        "overall": r"Overall skewness:\s+([\d.-]+)",
        "positive": r"Positive skewness:\s+([\d.-]+)",
        "negative": r"Negative skewness:\s+([\d.-]+)"
    }
    for key, pattern in skew_patterns.items():
        match = re.search(pattern, log_text)
        if match:
            results["skewness"][key] = float(match.group(1))
    
    # 7. Information about extrema
    "Global surface minimum: -0.027510 a.u. at  -0.225417   0.366873  -1.831106 Ang"
    match = re.search(r"Global surface minimum:\s+[\S]+ a.u. at\s+(\S+)\s+(\S+)\s+(\S+) Ang",log_text)
    if match:
        results["minima"]= [float(match.group(1)), float(match.group(2)), float(match.group(3))]
    return results

# Add an addition tool
@mcp.tool()
def analyze_esp_surface(fchk_path, multiwfn_path=multiwfn_default, path=path_default):
    """
    The tools is used to analyze the ESP surface form of Gaussian fchk file with multiwfn.
    
    Parameters:
        fchk_path(str): fchk file with the path
        multiwfn_path(str):  a path for a binary executable multiwfn
        path(str): a path for a directory where the output files will be stored
    """
    # Directly validate the user-provided path
    if not os.path.isfile(multiwfn_path):
        raise FileNotFoundError(f"The specified Multiwn executable file does not exist: {multiwfn_path}")
    
    # Use temporary files to ensure thread safety
    #print(os.getcwd())
    script_path = "multiwfn_script.txt"
    output_path = "output.log"
    
    try:
        path_old = os.getcwd()
        os.chdir(path)
        # Create Multiwfn command script
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(f"{fchk_path}\n")  # input fchk file path
            f.write("12\n")            # 12: quantitative molecular surface analysis
            f.write("0\n")             # 0: default parameters
            f.write("-1\n")            # 10: Export ESP extreme values data​
            f.write("-1\n")             # 9: Export surface vertex data
            f.write("q\n")             # q: quit

        # Run Multiwfn
        with open(script_path, "r", encoding="utf-8") as inp, \
             open(output_path, "w", encoding="utf-8") as out:
            subprocess.run(
                [multiwfn_path],
                stdin=inp,
                stdout=out,
                stderr=subprocess.STDOUT,
                text=True,
                check=True
            )

        # Parse results
        
        with open(output_path, "r", encoding="utf-8") as result_file:
            #print(result_file.read())
            results = parse_multiwfn_surface_analysis(result_file.read())
        os.chdir(path_old)

        return results

    finally:
        # Clean up temporary files
        for temp_file in [script_path, output_path]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass  # Prevent cleanup failures from affecting the main logic



if __name__ == "__main__":
    # Support command-line options for network access
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Gaussian MCP Server')
    parser.add_argument('--host', default='127.0.0.1', 
                       help='Host to bind to (use 0.0.0.0 for remote access)')
    parser.add_argument('--port', type=int, default=8000, 
                       help='Port to bind to')
    parser.add_argument('--remote', action='store_true',
                       help='Enable remote access (equivalent to --host 0.0.0.0)')
    
    # If no arguments are given, use the default MCP mode
    if len(sys.argv) == 1:
        mcp.run()
    else:
        args = parser.parse_args()
        
        # If --remote is specified, set host to 0.0.0.0 automatically
        if args.remote:
            args.host = '0.0.0.0'
        
        print(f"Start Gaussian MCP server...")
        print(f"Address: http://{args.host}:{args.port}")
        print(f"Remote Access​​: {'Enabled' if args.host == '0.0.0.0' else 'Disabled'}")
        print(f"Shut down​: Ctrl+C")
        print("-" * 50)
        
        # Start in network mode
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    