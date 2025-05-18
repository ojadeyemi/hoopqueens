### Data Pipeline Overview

This section outlines the logic and workflow for the data pipeline used in this project.

#### **Pipeline Components**

1. **Source Data**: The raw PDF files containing box scores at the end of a game.
2. **Data Preparation**: Extracting key information from the PDFs into a structured format and performing validation.
3. **Data Storage**: Storing the processed data in an SQLite database.
4. **Data Access**: Creating an API to stream the data for further use.
5. **Visualization**: Using a Streamlit UI to preview the workflow and interact with the data.

![Data Pipeline Overview](data_pipeline.png)

---

### **Workflow: From Raw PDF to SQLite Database**

#### **1. Input: Raw Box Score PDFs**

- At the end of each game, box score data is provided in PDF format.
- These PDFs serve as the source data for the pipeline.

#### **2. Parsing the PDFs**

- The pipeline processes the PDFs to extract key information, including:
  - **Player Box Scores**: Points, assists, rebounds, etc., for each player.
  - **Team Box Scores**: Aggregated statistics for the entire team.
- The extracted data is validated to ensure accuracy and completeness.

#### **3. Storing the Data**

- The validated data is stored in an SQLite database.
- The database schema is designed to support both player-level and team-level statistics.

#### **4. Previewing the Data**

- A Streamlit UI is used to preview the workflow and interact with the stored data.
- The UI allows you to:
  - View player and team statistics.
  - Search and filter data for specific games or players.

---

### **Key Benefits**

- **Automation**: Eliminates manual data entry by automating the extraction process.
- **Validation**: Ensures the data is accurate and reliable.
- **Accessibility**: Provides an easy-to-use interface for interacting with the data.

This pipeline streamlines the process of transforming raw game data into actionable insights.
