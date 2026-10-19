# Project 2 Report: University Class Scheduling & Timetable Optimization

> [!IMPORTANT]
> **AUTOGRADER COMPLIANCE INSTRUCTIONS:**
> This report is parsed automatically by the autograder. To ensure you receive full credit for your work:
> 1. **Do not modify** the section headers (`## ...`) or bold field keys (e.g., `**Name:**`, `**Total Courses Configured:**`, `**Video Presentation Link:**`, etc.).
> 2. **Write your answers directly after** the colon `:` of each field, replacing the placeholder text completely (including the outer brackets `[` and `]`).
> 3. **Maintain the file structure**. Changing headers, bold titles, or deleting lines can cause the autograder to miss your responses and award 0 marks.

---

## Student Information 
- **Name:** Daniel Montesdeoca
- **UID (netID):** dmont21
- **UIN:** 654966860

---

## Section 1: Dataset & University Configuration
- **Total Courses Configured:** 65
- **Total Rooms Configured:** 20
- **Total Time Slots Configured:** 50

---

## Section 2: Local Verification & Implemented Solvers
*Check the algorithms and features you successfully ran and verified by placing an `x` in the brackets (e.g., `[x]`):*
- [x] DataLoader & CSV Parsing
- [x] Hard Constraint Validation Engine
- [x] Soft Penalty & Quality Evaluation Engine
- [x] CSP Backtracking with MRV + LCV + Forward Checking
- [x] Min-Conflicts CSP Local Search
- [x] Timetable CSV Export (<studentid>_timetable.csv)

---

## Section 3: Video Presentation & Project Structure
- **Video Presentation Link:** [Provide an accessible link to your 5–7 minute video presentation]
- **Project Directory Structure:** The data is in the data file consisting of all of the csv files and the main executed code is in app.py which takes from the helper files such as softCon.py, labAdapt.py, and otherHelpers.py 

---

## Section 4: Discussion & Problem Formulation
*Provide your written analysis for each point by replacing the bracket placeholders below:*
- **How did you formulate the variables, domains, and constraints for this scheduling problem?**
The variables are formulated through the csv files that are givven and they are loaded into a data set which allows for me to access them through my backtracking.py file. I needed to make an adapter in order for it to work in the whole program.
- **Compare CSP Backtracking (with heuristics) vs Local Search (Min-Conflicts) in terms of scalability, completeness, and solution quality.**
In terms of completeness we can see that CSP backtracing is complete while local search tends to not be fully complete meaning it can get stuck and not find a specific solution. When it comes to scalability it depends on the size but local search tends to work better with larger data sets. 
- **How can modern AI / LLM techniques be combined with CSP solvers for real-world automated university scheduling?**
When combinding modern AI with these techniques it could make secheduling a lot easier and not have to worry about either overbooking a class or even determine if a studen is going to be able to take a class. AI can help in general speed up the scheduling process and cause less stress for both students and professors. 
