Put together a roadmap for the backend API of an app using python+FasAPI. Scalability and readability are a priority, with features organized in folders by domain rather than function (i.e. prefer "app/users/router.py" and "app/projects/router.py" over "app/routers/users.py" and "app/routers/projects.py"). Specifically, make an actionable, ordered to-do checklist to use to go from nothing to initial codebase based on the parameters described. Following this list will let me put together this app incrementally, beginning with entering basic seed data, and continuing to scale things with db migrations and organized, clean folder structures.

The app will be a joint project management portal to be used internally at an environmental monitoring company in order to track progress of jobs done for the New York City School Construction Authority (referred to as NYCSCA or just SCA).

NOTE: * next to a column will denote a required field

The main table to track projects will be:

  Table: projects
  Descriptions: Main schema organizing the work being tracked for a single project
  Columns:
    - project_num* - string, unique - project number denoted by string of pattern \d{2}-\d{3}-\d{4}. Internally, the first 2 digits denote the year the project was opened, the middle denote the kind of work being done, and the last 4 are just the project number
    - project_type* - enum - type of project (i.e. "Monitor PO18", "Emergency Monitoring", "Survey & Design", "Monitor & Survey PO18", etc...)
    - status* - enum - active, completed, postponed, cancelled

The "base" data (or the data that will at least not grow as much in terms of rows) consists of the following tables:

  Table: schools
  Description: locations where field work is happening
  Columns:
    - name* - string - name of the school
    - code* - string, unique - an overwhelming majority of the time this is a 4 character code following the pattern "[MRXQK]\d{3}", but there are some exceptions (i.e. "X985 @ X145", "X607 @ XAJF", and "KBND" are all real codes as well )
    - address* - string - the street address of the school
    - borough* - enum - Brooklyn | Manhattan | Bronx | Queens | Staten Island
    - state* - enum - two char state code in theory, but really just NY since schools all in same state
    - zip* - string - school's zip code


  Table: deliverables
  Description: Documents that have to be submitted and approved by SCA before we can submit a project for billing
  Columns:
    - name* - string - name of deliverable
    - description - string - description of what documents are needed for this deliverable


  Table: work_auths
  Description: SCA work authorizations 
  Columns:
    - wa_num - str, unique - WA number
    - service_id - str, unique - service if for WA
    - project_num - str, unique - project number for WA

  Table: wa_codes
  Description: SCA code corresponding to various work scopes of project
  Columns:
    - code* - string, unique - work type code
    - description* - string, unique - work type label/description
    - level* - enum - project | building

  Table: contractors
  Description: contracting company doing the work (usually asbestos abatement)
  Columns: 
    - name* - string, unique - name of company
    - address* - string - street address of company
    - city* - string
    - state* - enum - two char state code (not all contractors based in NY)
    - zip* - string - zip code
  
  Table: hygienists
  Description: SCA employees responsible for schools within different areas
  Columns:
    - first_name* - string - first name of employee
    - last_name* - string - last name of employee
    - email - string, unique - valid email 
    - phone - string, unique - phone number


  Table: employees
  Description: company employees doing field work
  Columns:
    - first_name* - string - first name of employee
    - last_name* - string - last name of employee
    - title - enum - Mr., Ms., Mrs., etc...
    - email - string, unique - valid email 
    - phone - string, unique - phone number
    - adp_id - string, unique - internal employee ID


  Table: users
  Description: users who can log in and interact with app
  Columns:
    - first_name* - string - first name of employee
    - last_name* - string - last name of employee
    - username* - string - display name to be used in templates (i.e. "Welcome {username}"). On user create, if blank then default to "{first_name} {last_name}"
    - hashed_password* - string
    - email - string, unique - valid email 
    - phone - string, unique - phone number
    - adp_id - string, unique - internal employee ID

Additionally, there'll be roles for both employees and users.

  For users, specific permissions (i.e. projects:write, schools:create, etc...) will be attached to roles, which will be assigned to users and used to restrict API actions

  For employees, specific roles will be assigned to determine the kind of work they're able to do (i.e. if they're a Project Monitor or Air Tech, they can collect air samples, if they're a Lead Risk Assessor, they can collect lead-in-dust-wipe samples). Employees can have multiple roles. A role/employee link assigning the employee a rols also needs a start date (required) and an end date (optional), as well as an hourly rate (required).
  
  Example: Say an employee has the following roles associated with them
    - Air Monitor - 12/1/24-11/30/25 - $45.00/hr
    - Air Monitor - 12/1/25-11/30/26 - $55.60/hr

  So if someone tried entering a time entry for this employee working as an air monitor:
    Time entry    ->    Outcome
    11/27/25 - 5:00PM-3:00AM    ->    We'd want to bill 12 hours at $45.00/hr
    12/27/25 - 5:00PM-3:00AM    ->    We'd want to bill 12 hours at $55.60/hr
    11/30/25 - 5:00PM-3:00AM    ->    We'd want to bill 9 hours at $45.00/hr, and 3 hours at $55.60/hr
    12/27/26 - 5:00PM-3:00AM    ->    Time entry insert will be invalid, since role not active during date

  Lastly, no two roles of the same type can overlap chronologically (two roles/rates can't be active for the same employee on a single day)

  NOTE: I'd like feedback on whether the employees and users tables would be better combined or left separate. The fields in both tables are very similar, and some users will also be in the employee table, but their distinct purposes and roles makes me lean towards separating them.

I also need to establish the following relationships between the tables:

  - Table: projects_schools_links
  - Relationship: projects <-> schools (many-to-many)
  - Notes: Projects require at least one school to take place in. Most of the time the project will be at only one school, but occassionally a project spans across more locations
  
  - Table: projects_contractors_links
  - Relationship: projects <-> contractors (many-to-many)
  - Notes: Projects can be done with any number of contractors. Since the contractors do abatement work, then if there's no abatement work then no contractor will be associated with the project. Most of the time, only one contractor will be on the project for its entirety, but occassionally additional contractors can work on a single project
  
  - Table: hygienist_projects_links
  - Relationship: hygienists -> projects - one-to-many
  - Notes: one hygienist works as the primary SCA contact for this project 
  
  - Table: manager_projects_links
  - Relationship: users -> projects (one-to-many)
  - Notes: projects are assigned a user to manage them. a user can have many projects assigned, but a project should belong to one user at a time at most. I want to keep an audit trail to keep track of when project assignments are updated and who is being assigned and/or taken off
  

The tables that will grow the most are the ones I need to most help with. I'd like some insights on how to best handle the work flow described

  Table: time_entries
  Description: Log billable on-site time by an employee against a project's school (so referencing a projects_schools_links)
  Columns:
    - date* - date (not a timestamp)
    - start_time - time
    - end_time - time
    - employee - foreign key to employee.id
    - activity - under which employee role is the employee working?
    - location - foreign key to projects_schools_links
    - project - foreign key to location.projectId
  Notes:
    Would appreciate some thoughts on how to handle all this nested and conditional referencing

  Table: lab_results
  Descriptions: Information related to sample results taken for project. A related against time_entries
  Columns:
    - batch_num* - string, unique - unique identifier for any set/batch of samples
    - is_report* - bool - False means we have just the handwritten COC on file, True means we've received the typed lab report for this batch
  Notes:
    I want help deciding on a schema for this type of data. Most of the samples are either PCM or TEM and need to track the following:
      - monitor* - employee who took samples
      - date* - date samples were collected
      - quantity* - # of samples collected
      - time_started* - time sample collection started
      - time_relinquished: time samples were dropped off at lab
      - turnaround_time* - enum - (if TEM) 3hr, 6hr, or 24hr / (if PCM) 1hr, 6hr, or 24hr
    The other common type of sampling done is bulk sampling, which can't be tracked the same way. The differences are:
      - inspectors - the COC for a single batch of bulk sample could be taken by multiple employees rather than just one
      - quantities - while a single batch of PCM or TEM samples will consist of a quantity of samples analyzed within a turnaround_time, bulk samples are counted as 4 different types of samples: PLM, NOB-PLM, NOB-PREP, and NOB-TEM
      - time started/relinquished: don't need to track these times (values are optional)
    Along with vermiculite, bulk, PCM, and TEM sampling make up the ACM testing that can be done for a project. There's also LBP and PCB sampling that could be done.
    What I'm still undecided on is whether I should make different tables for each kind of sampling, or if there's a way to normalize this information enough for a single lab_results table to track them all.

More complicated relationships

  The hierarchy of a project is as follows:

  - Internally a project is opened for a school
  - If a work authorization (WA) is issued, it will contain the work codes related to the project.
    - project level codes are assigned to individual projects. these have a flat fee associated with them (LAMP20 pays $750)
    - building level codes are assigned to schools belonging to a project. These represent work done at a site, and are billed hourly based on the rate of the employee conducting the work.
  - Based on the codes, certain deliverables will be needed. For example, if a project has a school with a LAMP33, then a Final Report will be required. If a project has a LAMP20 code, it will need both a Survey Report and a Job Scope as deliverables.
  - Going the other way, if certain work is done, the project will need the appropriate codes to be able to bill the work. For example, if a school only has a LAMP33 code but lead in dust wipe samples were taken, we'd need to add LAMP42 and LAMP43.
  - We can request amendments to the WA to add and/or remove the codes from the SCA.

  So say we open a job, but no WA is issued yet. If a project manager gets the COC for sample results from a lab for the project (i.e. PCM samples collected 1/1/26 by Bob for project 26-213-0666 at K505), then the manager would want to be able to note:
    - Bob was at K505 on 1/1/26 for project 26-213-0666 (add time_entry without start/stop for this project_school_link)
    - Bob took samples (add lab_result row to above time entry). We're still waiting on the typed report.
    - NOTE: if Bob doesn't have valid role for the type of work done, this entry won't create. Manager will want to leave note on project stating that monitor doesn't appear to have been licensed that date, and the project will be flagged as having a blocking issue.
    - Since air monitoring was done, project knows it needs building level codes LAMP30, LAMP32, LAMP33 added for K505
    - Since LAMP33 is needed, know school will need Final Report as a deliverable
    - Final Report will be marked as "pending WA", since there's nowhere to submit the final report until the WA is issued
  
  Later the manager receives Bob's daily logs. He can now update the time entry:
    - On 1/1/26, Bob was at K505 from 9am-11pm
  
  With this information, the manager can also prepare the final report, though he still can't submit it since no WA is issued. He should have a way of noting that, internally, it's available and ready to be uploaded.  
  
  A few days later, the SCA issues the WA, which has a LAMP20  project level code. The manager enters the WA into the system and relates it to 26-213-0666.
   - Since WA has LAMP20, the project will need Survey Report and Job Scope as deliverables. Project should show these deliverables as "outstanding"
   - Since we're missing the other required LAMP codes, project should note "Request for Amendment (RFA) needed to add LAMP30, LAMP32, and LAMP33"
   - Since LAMP33 isn't yet on the WA yet, the status should show "Pending RFA"
  
  The manager submits the RFA requesting the changes needed
   - The project should note "RFA under review to add LAMP30, LAMP32, and LAMP33"
   - The project wa_codes should also reflect which are needed, which have been submitted to be added, and which are actually on the last issued RFA
  
  The manager then submit the outstanding deliverables, and updates their status internally to "Under Review"

  A few days later, the RFA is approved, so the manager marks it as complete, and the codes in the app all show as actually being on the WA. The final report deliverable's status changes from "Pending RFA" to "Outstanding." The manager then uploads the final report to the SCA portal, and updates the deliverable from "Outstanding" to "Under review"

  A few more days later, the manager sees the deliverables were all approved, so he updates their statuses to "Approved." The project sees that no RFA is needed, and all the deliverables are submitted and approved, so the project gets marked as "Ready to bill"

Wrapping it up

This is just the initial starting point for this app, and there are more conditions and statuses that will need to be handled, so the most important thing I need out of this is a scalable, modular, and future-proof structure that can be expanded to allow for more specific flows to be encoded. For example, certain projects need a document from the abatement contractor. Some need this document as a deliverable. Projects will also need to track whether certain documents are saved in our files (for example, do we have the scans of the employee's log books corresponding to each time entry they claim). I need a flexible but intuitive way of defining the needs of a project and it's overall status.

The final purpose of this is to make the clearest frontend dashboard so managers can look up views like:
  - All active projects assigned to me with outstanding deliverables
  - All active projects needing an RFA submitted
  - All active projects waiting on an RFA
  - All active projects where everything is ready except the one document the contractor needs to share
  - All active projects ready to be submitted for billing
  - etc...
