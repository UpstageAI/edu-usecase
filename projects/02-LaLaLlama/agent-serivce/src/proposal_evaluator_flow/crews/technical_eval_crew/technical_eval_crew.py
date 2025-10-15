# crews/technical_eval_crew/technical_eval_crew.py
import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.llm import LLM
from dotenv import load_dotenv

load_dotenv()

@CrewBase
class TechnicalEvalCrew():
    """TechnicalEvalCrew crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self) -> None:
        # Hugging Face Inference API에서 지원하는 모델 사용
        self.llm = LLM(
            # model="huggingface/mistralai/Mixtral-8x7B-Instruct-v0.1", # 불가능
            model="huggingface/meta-llama/Meta-Llama-3-8B-Instruct", # 가능
            # model="huggingface/google/gemma-7b-it",
            api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            temperature=0.7,
            max_tokens=2048
        )

    # def __init__(self) -> None:
    #     # 빠른 Llama 3.2 모델 사용
    #     self.llm = LLM(
    #         model="ollama/llama3.2",
    #         base_url="http://localhost:11434"
    #     )

    @agent
    def technical_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['technical_analyst'],
            llm=self.llm,
            verbose=True
        )

    @agent
    def management_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['management_analyst'],
            llm=self.llm,
            verbose=True
        )

    @task
    def technical_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['technical_analysis_task'],
            agent=self.technical_analyst()
        )

    @task
    def management_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['management_analysis_task'],
            agent=self.management_analyst()
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )