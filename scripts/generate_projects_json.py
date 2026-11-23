"""Generate the ProjectPilot AI project database in JSON format."""

from __future__ import annotations

import json
from pathlib import Path


OUTPUT_PATH = Path("data/projects.json")

DIFFICULTIES = {
    "Beginner": {
        "suffix": "BEG",
        "times": ["1-3 Days", "4-7 Days", "8-15 Days"],
        "skills": ["Basic programming", "Data handling", "UI basics", "Debugging", "Project documentation"],
        "libraries": ["Pandas", "NumPy", "Streamlit", "Scikit-learn"],
        "roadmap": [
            "Understand the problem statement",
            "Set up the project structure",
            "Build the core feature",
            "Test with sample inputs",
            "Create a simple user interface",
        ],
    },
    "Intermediate": {
        "suffix": "INT",
        "times": ["8-15 Days", "16-30 Days"],
        "skills": ["API integration", "Database design", "Model comparison", "Backend development", "Testing"],
        "libraries": ["FastAPI", "Flask", "SQLAlchemy", "Scikit-learn", "Plotly"],
        "roadmap": [
            "Design the system workflow",
            "Build data and API layers",
            "Implement multiple approaches",
            "Evaluate results and edge cases",
            "Deploy a usable prototype",
        ],
    },
    "Advanced": {
        "suffix": "ADV",
        "times": ["16-30 Days", "1-3 Months"],
        "skills": ["Deep learning", "Distributed systems", "MLOps", "Cloud deployment", "Security hardening"],
        "libraries": ["PyTorch", "TensorFlow", "Docker", "Kubernetes", "MLflow"],
        "roadmap": [
            "Define architecture and success metrics",
            "Build scalable data pipelines",
            "Train or integrate advanced models",
            "Add monitoring and deployment automation",
            "Validate performance, reliability, and ethics",
        ],
    },
}

DOMAINS = [
    {
        "code": "AI",
        "name": "Artificial Intelligence",
        "subdomains": ["Expert Systems", "AI Agents", "Knowledge Graphs", "Planning", "Conversational AI"],
        "nouns": ["Study Assistant", "Decision Helper", "Research Navigator", "Task Planner", "Knowledge Coach"],
        "languages": ["Python", "Python; JavaScript", "Python; TypeScript"],
        "datasets": ["Generated User Intent Dataset", "Open Assistant Conversations", "Custom Knowledge Base"],
        "apis": ["OpenAI API", "Hugging Face Inference API", "Not applicable"],
    },
    {
        "code": "ML",
        "name": "Machine Learning",
        "subdomains": ["Classification", "Regression", "Clustering", "Model Evaluation", "Feature Engineering"],
        "nouns": ["Predictor", "Classifier", "Scoring Engine", "Forecast Tool", "Insight Model"],
        "languages": ["Python", "Python; SQL", "R; Python"],
        "datasets": ["UCI Machine Learning Repository", "Kaggle Tabular Dataset", "Generated Training Dataset"],
        "apis": ["Not applicable", "FastAPI Service", "Kaggle API"],
    },
    {
        "code": "DL",
        "name": "Deep Learning",
        "subdomains": ["Neural Networks", "CNNs", "RNNs", "Transformers", "Representation Learning"],
        "nouns": ["Neural Classifier", "Feature Learner", "Signal Recognizer", "Pattern Detector", "Training Pipeline"],
        "languages": ["Python", "Python; CUDA", "Python; JavaScript"],
        "datasets": ["MNIST", "CIFAR-10", "Generated Deep Learning Dataset"],
        "apis": ["Not applicable", "Weights and Biases API", "Hugging Face API"],
    },
    {
        "code": "DS",
        "name": "Data Science",
        "subdomains": ["Exploratory Analysis", "Visualization", "Statistics", "Dashboards", "Data Cleaning"],
        "nouns": ["Analytics Dashboard", "Trend Explorer", "Insight Report", "Data Story", "Metric Monitor"],
        "languages": ["Python", "Python; SQL", "R"],
        "datasets": ["Kaggle Public Dataset", "World Bank Open Data", "Generated Analytics Dataset"],
        "apis": ["Not applicable", "World Bank API", "Open Data API"],
    },
    {
        "code": "NLP",
        "name": "Natural Language Processing",
        "subdomains": ["Text Classification", "Information Extraction", "Summarization", "Question Answering", "Sentiment Analysis"],
        "nouns": ["Text Analyzer", "Document Assistant", "Sentiment Monitor", "Summary Builder", "Question Answering Tool"],
        "languages": ["Python", "Python; JavaScript", "Python; TypeScript"],
        "datasets": ["IMDb Reviews", "AG News", "Generated Text Dataset"],
        "apis": ["Hugging Face API", "OpenAI API", "Not applicable"],
    },
    {
        "code": "CV",
        "name": "Computer Vision",
        "subdomains": ["Image Classification", "Object Detection", "OCR", "Image Segmentation", "Pose Estimation"],
        "nouns": ["Image Inspector", "Object Finder", "Visual Quality Checker", "OCR Reader", "Camera Analyzer"],
        "languages": ["Python", "Python; C++", "Python; JavaScript"],
        "datasets": ["COCO Subset", "Open Images Dataset", "Generated Image Dataset"],
        "apis": ["Not applicable", "Google Vision API", "Roboflow API"],
    },
    {
        "code": "RS",
        "name": "Recommendation Systems",
        "subdomains": ["Collaborative Filtering", "Content-Based Filtering", "Hybrid Recommendations", "Ranking", "Personalization"],
        "nouns": ["Recommendation Engine", "Personalized Finder", "Ranking System", "Match Score Tool", "Suggestion Dashboard"],
        "languages": ["Python", "Python; SQL", "Python; JavaScript"],
        "datasets": ["MovieLens Dataset", "Amazon Reviews Subset", "Generated User Interaction Dataset"],
        "apis": ["Not applicable", "TMDB API", "Spotify API"],
    },
    {
        "code": "WEB",
        "name": "Web Development",
        "subdomains": ["Frontend", "Backend", "Full Stack", "Authentication", "Web APIs"],
        "nouns": ["Web Portal", "Admin Panel", "Booking Site", "Content Platform", "Service Dashboard"],
        "languages": ["JavaScript", "TypeScript", "Python; JavaScript", "PHP; JavaScript"],
        "datasets": ["Generated Web App Records", "Sample User Dataset", "Not applicable"],
        "apis": ["REST API", "Stripe API", "Not applicable"],
    },
    {
        "code": "MOB",
        "name": "Mobile App Development",
        "subdomains": ["Android Apps", "iOS Apps", "Cross-Platform Apps", "Offline Apps", "Mobile UX"],
        "nouns": ["Mobile Companion", "Tracking App", "Planner App", "Alert App", "Community App"],
        "languages": ["Dart", "Kotlin", "Swift", "JavaScript; TypeScript"],
        "datasets": ["Generated Mobile App Dataset", "Sample User Activity Data", "Not applicable"],
        "apis": ["Firebase API", "Google Maps API", "Not applicable"],
    },
    {
        "code": "CYB",
        "name": "Cybersecurity",
        "subdomains": ["Network Security", "Application Security", "Threat Detection", "Cryptography", "Security Awareness"],
        "nouns": ["Security Scanner", "Threat Dashboard", "Audit Helper", "Password Analyzer", "Incident Tracker"],
        "languages": ["Python", "Python; Bash", "Go", "JavaScript"],
        "datasets": ["Generated Security Logs", "CICIDS Dataset", "Phishing URL Dataset"],
        "apis": ["VirusTotal API", "Have I Been Pwned API", "Not applicable"],
    },
    {
        "code": "CLOUD",
        "name": "Cloud Computing",
        "subdomains": ["Serverless", "Cloud Storage", "Cloud Security", "Containers", "Cloud Monitoring"],
        "nouns": ["Cloud Dashboard", "Serverless Workflow", "Storage Manager", "Deployment Monitor", "Cost Optimizer"],
        "languages": ["Python", "Go", "TypeScript", "JavaScript"],
        "datasets": ["Generated Cloud Usage Logs", "Sample Billing Dataset", "Not applicable"],
        "apis": ["AWS API", "Google Cloud API", "Azure API"],
    },
    {
        "code": "DEVOPS",
        "name": "DevOps",
        "subdomains": ["CI/CD", "Monitoring", "Infrastructure as Code", "Containerization", "Release Automation"],
        "nouns": ["Pipeline Monitor", "Deployment Tracker", "Log Dashboard", "Release Assistant", "Build Health Tool"],
        "languages": ["Python", "Bash", "Go", "TypeScript"],
        "datasets": ["Generated CI Logs", "Sample Deployment Records", "Not applicable"],
        "apis": ["GitHub API", "Docker API", "Prometheus API"],
    },
    {
        "code": "IOT",
        "name": "Internet of Things (IoT)",
        "subdomains": ["Sensor Networks", "MQTT", "Smart Home", "Telemetry", "Edge Devices"],
        "nouns": ["Sensor Node", "Device Gateway", "Telemetry Dashboard", "Smart Controller", "Alert Device"],
        "languages": ["C++", "Python", "MicroPython", "JavaScript"],
        "datasets": ["Generated IoT Telemetry", "Sensor Time-Series Dataset", "Not applicable"],
        "apis": ["ThingSpeak API", "Firebase API", "MQTT Broker"],
    },
    {
        "code": "ROB",
        "name": "Robotics",
        "subdomains": ["Navigation", "Robot Vision", "Motion Control", "ROS", "Human-Robot Interaction"],
        "nouns": ["Robot Controller", "Navigation Assistant", "Motion Planner", "Vision Rover", "Task Bot"],
        "languages": ["Python", "C++", "Python; C++"],
        "datasets": ["Generated Robot Telemetry", "ROS Bag Dataset", "Not applicable"],
        "apis": ["ROS API", "Not applicable", "OpenCV API"],
    },
    {
        "code": "BC",
        "name": "Blockchain",
        "subdomains": ["Smart Contracts", "Wallets", "DeFi", "NFTs", "Supply Chain"],
        "nouns": ["Smart Contract App", "Wallet Tracker", "Token Dashboard", "Ledger Verifier", "Traceability Tool"],
        "languages": ["Solidity; JavaScript", "TypeScript", "Rust", "Go"],
        "datasets": ["Generated Transaction Dataset", "Ethereum Sample Data", "Not applicable"],
        "apis": ["Ethereum JSON-RPC API", "Etherscan API", "Not applicable"],
    },
    {
        "code": "GAME",
        "name": "Game Development",
        "subdomains": ["2D Games", "3D Games", "Game AI", "Level Design", "Multiplayer"],
        "nouns": ["Puzzle Game", "Arcade Challenge", "Level Editor", "NPC System", "Multiplayer Arena"],
        "languages": ["C#", "JavaScript", "C++", "Python"],
        "datasets": ["Generated Game Telemetry", "Not applicable", "Sample Player Behavior Dataset"],
        "apis": ["Unity API", "Godot API", "Not applicable"],
    },
    {
        "code": "ARVR",
        "name": "AR/VR",
        "subdomains": ["AR Interfaces", "VR Training", "Spatial Computing", "3D Interaction", "Immersive Learning"],
        "nouns": ["AR Guide", "VR Trainer", "Spatial Viewer", "Immersive Simulator", "3D Learning Lab"],
        "languages": ["C#", "JavaScript", "Swift", "Kotlin"],
        "datasets": ["Generated 3D Interaction Logs", "Not applicable", "Sample Training Scenario Dataset"],
        "apis": ["Unity XR API", "WebXR API", "ARCore API"],
    },
    {
        "code": "BD",
        "name": "Big Data",
        "subdomains": ["Batch Processing", "Streaming", "Data Lakes", "Distributed Analytics", "ETL"],
        "nouns": ["Data Pipeline", "Stream Processor", "ETL Monitor", "Lakehouse Dashboard", "Analytics Job"],
        "languages": ["Python", "Scala", "Java", "SQL"],
        "datasets": ["Generated Large Event Dataset", "NYC Taxi Dataset", "Common Crawl Sample"],
        "apis": ["Spark API", "Kafka API", "Not applicable"],
    },
    {
        "code": "DB",
        "name": "Database Systems",
        "subdomains": ["SQL Design", "NoSQL", "Query Optimization", "Data Modeling", "Transactions"],
        "nouns": ["Database Manager", "Query Analyzer", "Schema Designer", "Backup Tool", "Data Catalog"],
        "languages": ["SQL", "Python; SQL", "Java", "Go"],
        "datasets": ["Generated Relational Dataset", "Northwind Database", "Sample E-commerce Database"],
        "apis": ["PostgreSQL API", "MongoDB API", "Not applicable"],
    },
    {
        "code": "AUTO",
        "name": "Automation",
        "subdomains": ["Workflow Automation", "RPA", "Scripting", "Browser Automation", "Document Automation"],
        "nouns": ["Automation Bot", "Workflow Runner", "Report Generator", "Task Scheduler", "Data Entry Assistant"],
        "languages": ["Python", "JavaScript", "Bash", "PowerShell"],
        "datasets": ["Generated Workflow Records", "Sample Office Documents", "Not applicable"],
        "apis": ["Google Sheets API", "Notion API", "Not applicable"],
    },
    {
        "code": "EMB",
        "name": "Embedded Systems",
        "subdomains": ["Microcontrollers", "Sensors", "RTOS", "Wireless Modules", "Firmware"],
        "nouns": ["Sensor Controller", "Firmware Demo", "Device Monitor", "Signal Reader", "Low-Power Node"],
        "languages": ["C", "C++", "MicroPython", "Rust"],
        "datasets": ["Generated Sensor Logs", "Not applicable", "Device Telemetry Dataset"],
        "apis": ["MQTT Broker", "ThingSpeak API", "Not applicable"],
    },
    {
        "code": "UIUX",
        "name": "UI/UX Design",
        "subdomains": ["Design Systems", "Dashboard UX", "Mobile UX", "Accessibility", "User Research"],
        "nouns": ["Design System", "User Flow", "Dashboard Prototype", "Mobile Experience", "Research Repository"],
        "languages": ["HTML; CSS; JavaScript", "TypeScript", "Dart", "Swift"],
        "datasets": ["Generated Usability Notes", "Sample User Feedback Dataset", "Not applicable"],
        "apis": ["Figma API", "Not applicable", "UserTesting API"],
    },
]

INTERESTS = [
    "Healthcare",
    "Education",
    "Finance",
    "Agriculture",
    "Sports",
    "Gaming",
    "Entertainment",
    "E-commerce",
    "Environment",
    "Research",
    "Security",
    "Productivity",
    "Travel",
    "Smart Cities",
    "Music",
    "Social Media",
]

CONTEXTS = [
    "Student",
    "Campus",
    "Personal",
    "Community",
    "Small Business",
    "Research",
    "Smart City",
    "Healthcare",
    "Finance",
    "Agriculture",
]

ACTIONS = [
    "Assistant",
    "Analyzer",
    "Dashboard",
    "Planner",
    "Tracker",
    "Monitor",
    "Recommender",
    "Predictor",
    "Validator",
    "Explorer",
]


def pick(values: list[str], index: int) -> str:
    return values[index % len(values)]


def list_pick(values: list[str], start: int, count: int = 3) -> list[str]:
    return [pick(values, start + offset) for offset in range(count)]


def project_name(domain: dict, difficulty: str, index: int) -> str:
    context = pick(CONTEXTS, index)
    noun = pick(domain["nouns"], index)
    action = pick(ACTIONS, index + len(difficulty))
    if difficulty == "Beginner":
        return f"{context} {noun} {action}"
    if difficulty == "Intermediate":
        return f"{context} {noun} Workflow {action}"
    return f"Scalable {context} {noun} Intelligence {action}"


def dataset_link(dataset_name: str) -> str:
    if dataset_name == "Not applicable":
        return "Not applicable"
    if "Kaggle" in dataset_name:
        return "https://www.kaggle.com/datasets"
    if "UCI" in dataset_name:
        return "https://archive.ics.uci.edu/"
    if "COCO" in dataset_name:
        return "https://cocodataset.org/#home"
    if "MovieLens" in dataset_name:
        return "https://grouplens.org/datasets/movielens/"
    if "MNIST" in dataset_name or "CIFAR" in dataset_name:
        return "https://www.tensorflow.org/datasets"
    if "World Bank" in dataset_name:
        return "https://data.worldbank.org/"
    return "Not applicable"


def api_link(api_name: str) -> str:
    links = {
        "OpenAI API": "https://platform.openai.com/docs",
        "Hugging Face API": "https://huggingface.co/docs/api-inference",
        "Hugging Face Inference API": "https://huggingface.co/docs/api-inference",
        "TMDB API": "https://developer.themoviedb.org/docs",
        "Spotify API": "https://developer.spotify.com/documentation/web-api",
        "Stripe API": "https://stripe.com/docs/api",
        "Firebase API": "https://firebase.google.com/docs",
        "Google Maps API": "https://developers.google.com/maps/documentation",
        "VirusTotal API": "https://docs.virustotal.com/reference/overview",
        "Have I Been Pwned API": "https://haveibeenpwned.com/API/v3",
        "AWS API": "https://docs.aws.amazon.com/",
        "Google Cloud API": "https://cloud.google.com/apis",
        "Azure API": "https://learn.microsoft.com/azure/",
        "GitHub API": "https://docs.github.com/rest",
        "Docker API": "https://docs.docker.com/engine/api/",
        "Prometheus API": "https://prometheus.io/docs/prometheus/latest/querying/api/",
        "ThingSpeak API": "https://thingspeak.com/docs",
        "Ethereum JSON-RPC API": "https://ethereum.org/en/developers/docs/apis/json-rpc/",
        "Etherscan API": "https://docs.etherscan.io/",
        "Figma API": "https://www.figma.com/developers/api",
        "Mapbox API": "https://docs.mapbox.com/api/",
        "REST API": "Not applicable",
        "MQTT Broker": "Not applicable",
    }
    return links.get(api_name, "Not applicable")


def make_project(domain: dict, difficulty: str, index: int) -> dict:
    config = DIFFICULTIES[difficulty]
    status = "Pre-built" if index <= 30 else "Build from Scratch"
    subdomain = pick(domain["subdomains"], index)
    interest = pick(INTERESTS, index + len(domain["name"]))
    name = project_name(domain, difficulty, index)
    dataset_name = pick(domain["datasets"], index)
    api_name = pick(domain["apis"], index + 1)
    dataset_required = dataset_name != "Not applicable"
    api_required = api_name != "Not applicable"
    languages = pick(domain["languages"], index)
    libraries = list_pick(config["libraries"], index)
    skills = list_pick(config["skills"], index)
    tags = [
        domain["name"].lower().replace(" ", "-"),
        subdomain.lower().replace(" ", "-"),
        difficulty.lower(),
        interest.lower().replace(" ", "-"),
    ]

    project_id = f"{domain['code']}-{config['suffix']}-{index:03d}"
    description = (
        f"Build a {difficulty.lower()} {domain['name']} project for {interest.lower()} "
        f"that focuses on {subdomain.lower()} and delivers a usable {name.lower()}."
    )
    roadmap = config["roadmap"] + [
        f"Customize the solution for {interest.lower()} users",
        "Prepare README, screenshots, and demo instructions",
    ]
    future_scope = [
        "Add user accounts and saved preferences",
        "Deploy with monitoring and usage analytics",
        "Improve recommendations using feedback data",
    ]

    return {
        "project_id": project_id,
        "project_name": name,
        "domain": domain["name"],
        "subdomain": subdomain,
        "difficulty_level": difficulty,
        "estimated_completion_time": pick(config["times"], index),
        "programming_languages": languages,
        "interest_category": interest,
        "project_status": status,
        "short_description": description,
        "required_skills": skills,
        "required_libraries": libraries,
        "dataset_required": dataset_required,
        "dataset_name": dataset_name,
        "dataset_link": dataset_link(dataset_name),
        "api_required": api_required,
        "api_name": api_name,
        "api_link": api_link(api_name),
        "learning_roadmap": roadmap,
        "future_scope": future_scope,
        "github_search_keywords": f"{domain['name']} {subdomain} {name} {difficulty}".lower(),
        "tags": tags,
    }


def build_projects() -> list[dict]:
    projects = []
    for domain in DOMAINS:
        for difficulty in DIFFICULTIES:
            for index in range(1, 51):
                projects.append(make_project(domain, difficulty, index))
    return projects


def main() -> None:
    projects = build_projects()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "name": "ProjectPilot AI Project Database",
            "version": "1.0.0",
            "total_projects": len(projects),
            "domains": len(DOMAINS),
            "projects_per_domain_difficulty": 50,
            "status_distribution_per_50": {
                "Pre-built": 30,
                "Build from Scratch": 20,
            },
        },
        "projects": projects,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Generated {len(projects)} projects at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
