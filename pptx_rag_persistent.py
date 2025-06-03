
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from slide_vector_db_persistent import SlideVectorDB
from pptx_parser import PPTXParser

'''
작성자: 양건모
최초 생성일: 2025.06.02
-----------------------
변경 내역
2025.06.02 주석 추가
'''
class PPTXRAG:
    def __init__(self):
        '''변수 및 관련 모듈 초기화'''
        self.vectordb = SlideVectorDB()  # PersistentClient 기반으로 동작

        model_name = "google/gemma-3-4b-it"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto"
        ).to("cuda")

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.95,
        )
        self.llm = HuggingFacePipeline(pipeline=pipe)

    def process_pptx(self, pptx_path):
        '''pptx 파일 파싱'''
        parser = PPTXParser(pptx_path)
        slides = parser.parse_slides()
        self.vectordb.index_slides(slides)
        print(f"Indexed slides from {pptx_path}")

    def setup_rag_chain(self, slides):
        '''rag chain 설정'''
        template = """
        다음 정보를 바탕으로 질문에 답변해주세요:

        질문: {question}

        관련 슬라이드 내용:
        {context}

        답변:
        """
        prompt = PromptTemplate.from_template(template)

        def format_docs(docs):
            return "\n\n".join(
                [f"슬라이드 {d['slide_number']} - {d['text_content']} - {d['file_name']}" for d in docs]
            )

        return (
            {"context": lambda x: format_docs(slides), "question": lambda x: x["question"]}
            | prompt
            | self.llm
        )

    def query(self, question, k=3):
        '''질의'''
        slides = self.vectordb.query_slides(question, k=k)
        rag_chain = self.setup_rag_chain(slides)
        answer = rag_chain.invoke({"question": question})
        return {
            "answer": answer.content,
            "related_slides": slides
        }
