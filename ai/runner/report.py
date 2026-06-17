# from utils.logger import Logger
# from utils.io.files import load_json
# from utils.io.path import resolve_path
# from utils.io.text import write_text, append_text
# from utils.preprocessing import prepare_report_chunks
# from utils.artifacts.extractor import get_static_tools, get_threat_actor_message_blocks
# from config import REPORT_FILENAME, RESULT_FILENAME, THREAT_ACTOR_MESSAGES_FILENAME
# from ai.runner.base import BaseAIRunner
# from ai.generators.report import AIReport


# class ReportAIRunner(BaseAIRunner):
#     def __init__(self, context, model_registry):
#         super().__init__(context)

#         self.report_path = resolve_path(self.context.output, REPORT_FILENAME)

#         self.model_registry = model_registry
#         llm = self.model_registry.create_task_client("report", profile_override=self.context.profile)
#         self.report_generator = AIReport(llm)


#     def _get_static_tools(self) -> dict:
#         result = load_json(self.context.output, RESULT_FILENAME)
#         if not result:
#             Logger.warning("No static analysis data found. Skipping static report section.")
#             return {}

#         return get_static_tools(result)


#     def _append_report(self, report: str):
#         if report:
#             append_text(self.report_path, report.strip())
#         append_text(self.report_path, "\n")


#     def _save_static_data(self):
#         Logger.info("Reporting static analysis data")
#         self._append_report("\n## Static Analysis\n")
#         static_tools_data = self._get_static_tools()

#         for tool_name, tool_result in static_tools_data.items():
#             Logger.info(f"Reporting {tool_name} data")
#             if tool_result["status"] != "ok":
#                 continue
            
#             tool_data = tool_result.get("data", {})
#             chunks = prepare_report_chunks(tool_name, tool_data)

#             for chunk_index, chunk_data in enumerate(chunks, start=1):
#                 section = chunk_data.get("section") if isinstance(chunk_data, dict) else None
#                 if section:
#                     title = f"\n## {tool_name}: {section}"
#                 elif len(chunks) > 1:
#                     title = f"\n## {tool_name} {chunk_index}"
#                 else:
#                     title = f"\n## {tool_name}"

#                 self._append_report(title)
#                 report_tool_name = f"{tool_name}.{section}" if section else tool_name
#                 report = self.report_generator.analyze_and_report("Static", report_tool_name, chunk_data)
#                 self._append_report(report)
        
#         Logger.success("Static tools report finished")


#     def _save_static_agent_data(self):
#         Logger.info("Reporting static agent findings")
#         static_agent_data = load_json(self.context.output, THREAT_ACTOR_MESSAGES_FILENAME)
#         if not static_agent_data:
#             return
        
#         self._append_report("\n## Static Agent Findings\n")
#         blocks = get_threat_actor_message_blocks(static_agent_data)

#         for block in blocks:
#             report = self.report_generator.analyze_and_report("Static Agent", "static_agent", block)
#             self._append_report(report)

#         Logger.success("Static agent report finished")


#     def run(self):
#         Logger.info("Running AI mode")
#         write_text(self.report_path, "# Malware Analysis Report\n")
#         self._save_static_data()
#         self._save_static_agent_data()
#         Logger.success("Finish report")
