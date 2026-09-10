# Olist Kaggle Project — Context

## 1. Project Overview

This is a portfolio project focused on Data Engineering using the Brazilian E-Commerce Public Dataset by Olist.

The goal is to demonstrate practical Data Engineering skills through a reproducible data pipeline, data transformation, storage, SQL analysis, data quality, and a simple visualization layer.

The project should remain appropriate for a junior-to-mid-level Data Engineering portfolio.

The project is intentionally not designed to demonstrate advanced distributed systems or enterprise-scale infrastructure.

---

## 2. Source Dataset

Dataset:

Brazilian E-Commerce Public Dataset by Olist

Source:

Kaggle

Dataset ID:

olistbr/brazilian-ecommerce

The dataset contains approximately 100,000 orders from the Brazilian e-commerce ecosystem and is distributed across multiple relational CSV files.

Main files include:

- olist_customers_dataset.csv
- olist_geolocation_dataset.csv
- olist_order_items_dataset.csv
- olist_order_payments_dataset.csv
- olist_order_reviews_dataset.csv
- olist_orders_dataset.csv
- olist_products_dataset.csv
- olist_sellers_dataset.csv
- product_category_name_translation.csv

The dataset is downloaded through the Kaggle CLI rather than manually downloading files.

---

## 3. Current Local Environment

Operating system:

Ubuntu Linux

Project directory:

/home/kenji-soda/Documents/olist-kaggle project

Python:

Python 3.14.4

Virtual environment:

.venv/

The project uses a Python virtual environment to isolate project dependencies.

Kaggle CLI:

Installed inside the project's .venv.

Kaggle CLI version at project setup:

2.2.4

Kaggle authentication:

Configured and tested successfully.

Git:

Configured locally.

GitHub:

Repository:

https://github.com/brunosoda/olist-kaggle-project

Main branch:

main

GitHub CLI:

Installed and authenticated.

Git push:

Successfully tested.

---

## 4. Version Control

The project uses Git and GitHub.

The repository is public and intended to serve as a portfolio project.

A .gitignore file has already been created.

The .gitignore excludes:

- .venv/
- data/raw/
- .env
- Python cache files
- IDE-specific files
- operating-system files
- Kaggle API token files

Raw datasets and credentials must never be committed.

The first Git commit has already been created and pushed to GitHub.

---

## 5. Development Environment

The project is being developed using Google Antigravity.

Antigravity agents will have access to the project files and may assist with development.

Agents should treat this document as project context and the associated project Rule as persistent project constraints.

The user remains responsible for project decisions.

Agents should propose solutions, explain relevant trade-offs, and avoid making significant architectural decisions silently.

---

## 6. Project Philosophy

The project should prioritize:

1. Understanding the data
2. Reproducibility
3. Data quality
4. Clear transformations
5. Maintainable code
6. SQL proficiency
7. Practical Data Engineering concepts
8. Good documentation

The project should not become unnecessarily complex just to demonstrate more technologies.

Technologies such as Kafka, Spark, Airflow, Kubernetes, or complex cloud infrastructure should not be introduced unless there is a specific project requirement or a clear learning objective.

---

## 7. AI Usage

AI assistants and Antigravity agents may be used to help develop the project.

However, AI should not become part of the actual data pipeline unless explicitly decided later.

The project's data processing should remain understandable and reproducible without requiring an AI agent to execute the pipeline.

---

## 8. Current Project Status

Completed:

- Python verified
- Project virtual environment created
- Virtual environment activated
- Kaggle CLI installed
- Kaggle authentication configured
- Olist dataset downloaded
- .gitignore created
- Git configured
- GitHub repository created
- Initial Git commit created
- GitHub CLI installed
- GitHub authentication configured
- Initial push to GitHub completed

The project has not yet entered the implementation phase.

No ETL pipeline, database schema, analytical SQL, dashboard, or application architecture has been finalized yet.

---

## 9. Important Principle

Do not assume that decisions have been made simply because a technology was discussed.

Only treat a technology, architecture, schema, workflow, or implementation approach as an established project decision when it has explicitly been adopted.

When a new technical decision is proposed, explain the reason and trade-offs before treating it as part of the project architecture.
