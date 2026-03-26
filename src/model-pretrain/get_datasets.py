import os
import git
import requests
from zipfile import ZipFile
from roboflow import Roboflow

# Paths
RAW_DIR = "datasets/raw"
os.makedirs(RAW_DIR, exist_ok=True)

# -------------------------------
# 1. Azure Synthetic P&ID
# -------------------------------
azure_repo = "https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams.git"
azure_dir = os.path.join(RAW_DIR, "azure_pid")
if not os.path.exists(azure_dir):
    git.Repo.clone_from(azure_repo, azure_dir)
    print("Azure P&ID dataset cloned.")

# -------------------------------
# 2. Eng_Diagrams symbols
# -------------------------------
eng_repo = "https://github.com/heyad/Eng_Diagrams.git"
eng_dir = os.path.join(RAW_DIR, "eng_diagrams")
if not os.path.exists(eng_dir):
    git.Repo.clone_from(eng_repo, eng_dir)
    print("Eng_Diagrams dataset cloned.")

# -------------------------------
# 3. Kaggle P&ID symbol dataset
# -------------------------------
# Make sure kaggle.json is in ~/.kaggle/
kaggle_dataset = "hristohristov21/pid-symbols"
kaggle_dir = os.path.join(RAW_DIR, "kaggle_pid_symbols")
if not os.path.exists(kaggle_dir):
    os.makedirs(kaggle_dir, exist_ok=True)
    os.system(f"kaggle datasets download -d {kaggle_dataset} -p {kaggle_dir} --unzip")
    print("Kaggle P&ID symbols downloaded.")

# -------------------------------
# 4. PID2Graph Dataset (Zenodo)
# -------------------------------
pid2graph_url = "https://zenodo.org/records/14803338/files/PID2Graph.zip"
pid2graph_file = os.path.join(RAW_DIR, "PID2Graph.zip")
pid2graph_dir = os.path.join(RAW_DIR, "PID2Graph")
if not os.path.exists(pid2graph_dir):
    r = requests.get(pid2graph_url, stream=True)
    with open(pid2graph_file, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)
    with ZipFile(pid2graph_file, 'r') as zip_ref:
        zip_ref.extractall(pid2graph_dir)
    print("PID2Graph dataset downloaded and extracted.")

# -------------------------------
# 5. Roboflow P&ID dataset
# -------------------------------
# rf = Roboflow(api_key=os.getenv("ROBOFLOW_API_KEY"))
rf = Roboflow(api_key="dzR9k8uggXvkRNEFDeZw")
project = rf.workspace("pid-connect").project("p-id-symbols")
dataset = project.version(1).download("yolov8")
print("Roboflow dataset downloaded:", dataset.location)
