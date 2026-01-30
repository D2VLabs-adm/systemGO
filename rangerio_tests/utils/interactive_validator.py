"""
Interactive validator for human-in-the-loop validation
Displays results and collects user feedback
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import base64
from datetime import datetime


class InteractiveValidator:
    """
    Collects human feedback during test execution
    Generates beautiful HTML reports for human review
    Saves validated data to golden dataset
    """
    
    def __init__(self, golden_output_dir: Path):
        self.golden_output_dir = golden_output_dir
        self.validations = []
        self.golden_output_dir.mkdir(parents=True, exist_ok=True)
        self.html_items = []
        self.report_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def display_mode_comparison(
        self,
        query: str,
        query_type: str,
        expected_answer: str,
        mode_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Display side-by-side comparison of all modes for the same query.
        
        Args:
            query: The user's question
            query_type: Type of query (factual, analytical, ambiguous, etc.)
            expected_answer: What the correct answer should contain
            mode_results: Dict mapping mode_name -> result dict
        
        Returns:
            Validation dict for tracking
        """
        # Terminal output (for monitoring)
        print(f"\n{'='*80}")
        print(f"Mode Comparison - Query {len(self.html_items) + 1}")
        print(f"Query: {query}")
        print(f"Type: {query_type}")
        print(f"{'='*80}")
        
        for mode_name, result in mode_results.items():
            print(f"\n{mode_name.upper()}:")
            print(f"  Time: {result['response_time_ms']}ms")
            print(f"  Confidence: {result['confidence'].get('score', 'N/A')}")
            print(f"  Answer: {result['answer'][:80]}...")
        
        print(f"\n{'='*80}\n")
        
        # Add to HTML report
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'mode_comparison',
            'id': item_id,
            'query': query,
            'query_type': query_type,
            'expected_answer': expected_answer,
            'mode_results': mode_results
        })
        
        # Auto-validate (tests continue, human reviews later)
        validation = {
            "item_id": item_id,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review in HTML report",
            "modes_tested": list(mode_results.keys())
        }
        
        self.validations.append(validation)
        return validation
    
    def display_rag_answer(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Display RAG answer and add to HTML report
        
        Terminal output for monitoring + HTML report for detailed review
        
        Returns validation dict with is_accurate, timestamp, feedback
        """
        # Terminal output (for monitoring during test run)
        print(f"\n{'='*60}")
        print(f"Question {len(self.html_items) + 1}: {question}")
        print(f"Answer: {answer[:100]}...")
        print(f"Contexts: {len(contexts)} chunks")
        print(f"{'='*60}\n")
        
        # Add to HTML report
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'rag_answer',
            'id': item_id,
            'question': question,
            'answer': answer,
            'contexts': contexts,
            'metadata': metadata or {}
        })
        
        # Auto-validate for test continuation
        is_accurate = len(contexts) > 0 and len(answer) > 20
        
        validation = {
            "is_accurate": is_accurate,
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review in HTML report",
            "item_id": item_id,
            "question": question,
            "answer": answer,
            "num_contexts": len(contexts)
        }
        
        self.validations.append(validation)
        return validation
    
    def display_chart(
        self,
        chart_path: str,
        prompt: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Display chart and add to HTML report
        
        Returns validation dict
        """
        print(f"\n{'='*60}")
        print(f"Chart {len(self.html_items) + 1}: {prompt}")
        print(f"Path: {chart_path}")
        print(f"{'='*60}\n")
        
        # Encode image as base64 for embedding in HTML
        chart_data = None
        if chart_path and Path(chart_path).exists():
            try:
                with open(chart_path, 'rb') as f:
                    chart_data = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"Warning: Could not encode chart: {e}")
        
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'chart',
            'id': item_id,
            'prompt': prompt,
            'chart_path': chart_path,
            'chart_data': chart_data,
            'metadata': metadata or {}
        })
        
        validation = {
            "is_accurate": chart_path is not None,
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review in HTML report",
            "item_id": item_id,
            "chart_path": chart_path,
            "prompt": prompt
        }
        
        self.validations.append(validation)
        return validation
    
    def display_prompt_comparison(
        self,
        question: str,
        answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Show side-by-side prompt comparison and add to HTML report
        
        Returns validation dict
        """
        print(f"\n{'='*60}")
        print(f"Comparison {len(self.html_items) + 1}: {question}")
        print(f"Variations: {len(answers)}")
        for i, ans in enumerate(answers):
            print(f"  {i+1}. {ans['style']}: {ans['answer'][:50]}...")
        print(f"{'='*60}\n")
        
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'prompt_comparison',
            'id': item_id,
            'question': question,
            'answers': answers
        })
        
        # Auto-select structured or detailed styles
        best_style = None
        if any(a['style'] in ['structured', 'detailed_request'] for a in answers):
            best_style = next((a['style'] for a in answers if a['style'] in ['structured', 'detailed_request']), None)
        
        validation = {
            "is_accurate": True,
            "timestamp": datetime.now().isoformat(),
            "feedback": f"Pending human review - Auto-suggestion: {best_style}" if best_style else "Pending human review",
            "item_id": item_id,
            "question": question,
            "num_variations": len(answers),
            "best_style": best_style
        }
        
        self.validations.append(validation)
        return validation
    
    def save_validated_data(
        self,
        data: Any,
        filename: str
    ):
        """
        Save validated data to file
        
        Args:
            data: Data to save (dict, list, etc)
            filename: Output filename
        """
        output_file = self.golden_output_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✓ Validated data saved: {output_file}")
        
        return output_file
    
    def save_golden_dataset(self):
        """
        Save all validated answers to golden dataset for future automated testing
        """
        output_file = self.golden_output_dir / f"validated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.validations, f, indent=2)
        
        print(f"✅ Golden dataset saved: {output_file}")
        print(f"   Total validations: {len(self.validations)}")
        
        return output_file
    
    def generate_html_report(self):
        """
        Generate interactive HTML report for human review
        
        Returns path to generated HTML file
        """
        from rangerio_tests.utils.html_report_template import get_html_template
        
        # Start with base template
        html = get_html_template(self.report_id, len(self.html_items))
        
        # Insert validation items
        items_html = ""
        for item in self.html_items:
            if item['type'] == 'rag_answer':
                items_html += self._render_rag_item(item)
            elif item['type'] == 'rag_refinement':
                items_html += self._render_rag_refinement_item(item)
            elif item['type'] == 'multisource_validation':
                items_html += self._render_multisource_item(item)
            elif item['type'] == 'export_quality':
                items_html += self._render_export_quality_item(item)
            elif item['type'] == 'chart':
                items_html += self._render_chart_item(item)
            elif item['type'] == 'prompt_comparison':
                items_html += self._render_comparison_item(item)
            elif item['type'] == 'mode_comparison':
                items_html += self._render_mode_comparison_item(item)
        
        # Insert items into template
        html = html.replace('<!-- Items will be inserted here -->', items_html)
        
        # Save HTML report
        report_file = self.golden_output_dir / f"interactive_validation_{self.report_id}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n{'='*60}")
        print(f"✅ Interactive HTML Report Generated!")
        print(f"📂 Location: {report_file}")
        print(f"\n📝 Instructions:")
        print(f"   1. Open the HTML file in your browser")
        print(f"   2. Review each item and select accuracy rating")
        print(f"   3. Add notes for any items that need explanation")
        print(f"   4. Progress auto-saves every 30 seconds")
        print(f"   5. Click 'Export Results' when done")
        print(f"\n💡 Results will be saved to:")
        print(f"   validation_results_{self.report_id}.json")
        print(f"{'='*60}\n")
        
        return report_file
    
    def _render_rag_item(self, item):
        """Render RAG answer item as HTML"""
        contexts_html = ''.join(
            f'<div class="context"><strong>Context {i+1}:</strong> {ctx}</div>' 
            for i, ctx in enumerate(item['contexts'])
        )
        
        metadata_html = f'<div class="metadata">Metadata: {item["metadata"]}</div>' if item['metadata'] else ''
        
        # Decomposition info
        decomposition_html = ''
        if item.get('metadata') and isinstance(item['metadata'], dict):
            decomp = item['metadata'].get('decomposition', {})
            if decomp.get('was_decomposed'):
                sub_queries = decomp.get('sub_queries', [])
                if sub_queries:
                    sub_queries_html = ''.join(
                        f'<li><strong>Part {i}:</strong> {sq}</li>' 
                        for i, sq in enumerate(sub_queries, 1)
                    )
                    decomposition_html = f"""
                    <div class="decomposition-info" style="background: #1a3a52; padding: 12px; border-left: 4px solid #4a9eff; margin: 10px 0; border-radius: 4px;">
                        <h5 style="margin-top: 0; color: #4a9eff;">🔍 Query Decomposition</h5>
                        <p style="margin: 5px 0; color: #b0c4de;">This complex query was broken into {len(sub_queries)} simpler parts:</p>
                        <ol style="margin: 10px 0; padding-left: 20px; color: #e0e8f0;">
                            {sub_queries_html}
                        </ol>
                        <p style="margin: 5px 0; font-size: 0.9em; color: #8ba0b8;">Each part was answered independently, then combined for the final response.</p>
                    </div>
                    """
        
        return f"""
        <div class="validation-item" data-item-id="{item['id']}" data-item-type="rag_answer">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">RAG Answer</span>
            </div>
            
            <div class="question">❓ {item['question']}</div>
            
            {decomposition_html}
            
            <div class="answer">
                <strong>Answer:</strong><br>
                {item['answer']}
            </div>
            
            <div class="contexts">
                <strong>Retrieved Contexts ({len(item['contexts'])}):</strong>
                {contexts_html}
            </div>
            
            {metadata_html}
            
            <div class="validation-form">
                <h4>Your Validation:</h4>
                <div class="radio-group">
                    <div class="radio-option accurate">
                        <input type="radio" id="item{item['id']}_accurate" name="validation_{item['id']}" value="accurate">
                        <label for="item{item['id']}_accurate">✅ Accurate</label>
                    </div>
                    <div class="radio-option partial">
                        <input type="radio" id="item{item['id']}_partial" name="validation_{item['id']}" value="partial">
                        <label for="item{item['id']}_partial">⚠️ Partially Accurate</label>
                    </div>
                    <div class="radio-option inaccurate">
                        <input type="radio" id="item{item['id']}_inaccurate" name="validation_{item['id']}" value="inaccurate">
                        <label for="item{item['id']}_inaccurate">❌ Inaccurate/Hallucination</label>
                    </div>
                </div>
                <textarea name="notes_{item['id']}" placeholder="Add your notes here (optional)...&#10;&#10;Examples:&#10;- Answer is correct but could be more specific&#10;- Missing important context about X&#10;- Hallucinated the date/number&#10;- Great answer, fully supported by contexts"></textarea>
            </div>
        </div>
        """
    
    def _render_chart_item(self, item):
        """Render chart item as HTML"""
        if item['chart_data']:
            chart_html = f'<img src="data:image/png;base64,{item["chart_data"]}" alt="Generated Chart">'
        else:
            chart_html = f'<p>Chart file: {item["chart_path"]}</p>'
        
        return f"""
        <div class="validation-item" data-item-id="{item['id']}" data-item-type="chart">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Chart Validation</span>
            </div>
            
            <div class="question">📊 {item['prompt']}</div>
            
            <div class="chart-container">
                {chart_html}
            </div>
            
            <div class="validation-form">
                <h4>Your Validation:</h4>
                <div class="radio-group">
                    <div class="radio-option accurate">
                        <input type="radio" id="item{item['id']}_accurate" name="validation_{item['id']}" value="accurate">
                        <label for="item{item['id']}_accurate">✅ Accurate Chart</label>
                    </div>
                    <div class="radio-option partial">
                        <input type="radio" id="item{item['id']}_partial" name="validation_{item['id']}" value="partial">
                        <label for="item{item['id']}_partial">⚠️ Chart Has Issues</label>
                    </div>
                    <div class="radio-option inaccurate">
                        <input type="radio" id="item{item['id']}_inaccurate" name="validation_{item['id']}" value="inaccurate">
                        <label for="item{item['id']}_inaccurate">❌ Incorrect Chart</label>
                    </div>
                </div>
                <textarea name="notes_{item['id']}" placeholder="Add your notes here (optional)...&#10;&#10;Examples:&#10;- Chart shows correct data but wrong chart type&#10;- Labels are misleading&#10;- Data visualization is perfect&#10;- Colors make it hard to read"></textarea>
            </div>
        </div>
        """
    
    def _render_comparison_item(self, item):
        """Render prompt comparison item as HTML"""
        comparison_html = '<div class="comparison-grid">'
        for ans in item['answers']:
            comparison_html += f"""
                <div class="comparison-item">
                    <span class="style-tag">{ans['style']}</span>
                    <div><strong>Prompt:</strong> {ans.get('prompt', item['question'])}</div>
                    <div style="margin-top: 10px;"><strong>Answer:</strong><br>{ans['answer']}</div>
                </div>
            """
        comparison_html += '</div>'
        
        radio_options = ''.join(
            f'''<div class="radio-option accurate">
                <input type="radio" id="item{item["id"]}_opt{i}" name="validation_{item["id"]}" value="{ans["style"]}">
                <label for="item{item["id"]}_opt{i}">{ans["style"]}</label>
            </div>''' 
            for i, ans in enumerate(item["answers"])
        )
        
        return f"""
        <div class="validation-item" data-item-id="{item['id']}" data-item-type="prompt_comparison">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Prompt Comparison</span>
            </div>
            
            <div class="question">🔄 {item['question']}</div>
            
            {comparison_html}
            
            <div class="validation-form">
                <h4>Which approach works best?</h4>
                <div class="radio-group">
                    {radio_options}
                </div>
                <textarea name="notes_{item['id']}" placeholder="Add your notes here (optional)...&#10;&#10;Examples:&#10;- Structured prompts give more detailed answers&#10;- Direct approach is clearer&#10;- Role-based adds unnecessary verbosity"></textarea>
            </div>
        </div>
        """
    
    def display_query_with_refinement_feedback(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Display query with refinement checkboxes for specific issues
        
        Allows user to identify specific problems that need fixing:
        - Hallucinations
        - Incomplete reasoning
        - Missing data
        - Incorrect calculations
        - etc.
        
        Returns validation dict with refinement_needed flag
        """
        # Terminal output
        print(f"\n{'='*80}")
        print(f"Query {len(self.html_items) + 1}: {question}")
        print(f"Answer length: {len(answer)} chars")
        
        # Check for decomposition
        if metadata and metadata.get('decomposition', {}).get('was_decomposed'):
            sub_queries = metadata['decomposition'].get('sub_queries', [])
            print(f"🔍 DECOMPOSED into {len(sub_queries)} parts:")
            for i, sq in enumerate(sub_queries, 1):
                print(f"   {i}. {sq}")
        
        print(f"{'='*80}\n")
        print(f"Query {len(self.html_items) + 1} (Refinement Tracking)")
        print(f"Question: {question[:80]}...")
        print(f"Answer: {answer[:100]}...")
        print(f"{'='*80}\n")
        
        # Add to HTML report with refinement options
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'rag_refinement',
            'id': item_id,
            'question': question,
            'answer': answer,
            'contexts': contexts,
            'metadata': metadata or {},
            'expected_elements': metadata.get('expected_elements', []) if metadata else [],
            'potential_issues': metadata.get('potential_issues', []) if metadata else []
        })
        
        # Auto-validate for test continuation
        validation = {
            "is_accurate": len(answer) > 50 and len(contexts) > 0,
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review with refinement tracking",
            "item_id": item_id,
            "question": question,
            "answer": answer[:200],
            "refinement_tracking": True
        }
        
        self.validations.append(validation)
        return validation
    
    def display_multisource_query_validation(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        source_coverage: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Display multi-source query with coverage analysis
        
        Shows which sources contributed to the answer and whether
        all required sources were referenced.
        
        Returns validation dict with source coverage info
        """
        # Terminal output
        print(f"\n{'='*80}")
        print(f"Multi-Source Query {len(self.html_items) + 1}")
        print(f"Question: {question[:80]}...")
        print(f"Sources covered: {source_coverage['unique_sources']} ({source_coverage.get('coverage_pct', 0):.0f}%)")
        print(f"Answer: {answer[:100]}...")
        print(f"{'='*80}\n")
        
        # Add to HTML report
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'multisource_validation',
            'id': item_id,
            'question': question,
            'answer': answer,
            'contexts': contexts,
            'source_coverage': source_coverage,
            'metadata': metadata or {}
        })
        
        # Auto-validate
        required_source_count = len(metadata.get('required_sources', [])) if metadata else 0
        is_sufficient_coverage = source_coverage['unique_sources'] >= required_source_count if required_source_count > 0 else True
        
        validation = {
            "is_accurate": is_sufficient_coverage and len(answer) > 100,
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review with source coverage analysis",
            "item_id": item_id,
            "question": question,
            "answer": answer[:200],
            "source_coverage": source_coverage
        }
        
        self.validations.append(validation)
        return validation
    
    def display_export_quality_with_issues(
        self,
        export_info: Dict[str, Any],
        cleanup_instructions: str,
        cleanup_result: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Display export validation with quality tracking
        
        Allows user to verify:
        - Export file opens correctly
        - Data cleanup was applied correctly
        - Formatting is preserved
        - All tabs are present
        
        Returns validation dict with export quality info
        """
        # Terminal output
        print(f"\n{'='*80}")
        print(f"Export Quality Check {len(self.html_items) + 1}")
        print(f"Export successful: {export_info.get('export_successful', False)}")
        if 'file_path' in export_info:
            print(f"File: {export_info['file_path']}")
            print(f"Size: {export_info.get('file_size', 0)} bytes")
        print(f"{'='*80}\n")
        
        # Add to HTML report
        item_id = len(self.html_items)
        self.html_items.append({
            'type': 'export_quality',
            'id': item_id,
            'export_info': export_info,
            'cleanup_instructions': cleanup_instructions,
            'cleanup_result': cleanup_result,
            'metadata': metadata or {}
        })
        
        # Auto-validate
        validation = {
            "is_accurate": export_info.get('export_successful', False),
            "timestamp": datetime.now().isoformat(),
            "feedback": "Pending human review - please verify export quality",
            "item_id": item_id,
            "export_info": export_info
        }
        
        self.validations.append(validation)
        return validation
    
    def display_refinement_summary(self) -> Dict[str, Any]:
        """
        Generate summary of all queries that need refinement
        
        Returns dict with:
        - Total queries tested
        - Queries needing refinement
        - Common issues identified
        - Priority fixes
        """
        # This will be called at the end of test run
        refinement_items = [v for v in self.validations if v.get('refinement_tracking')]
        
        print(f"\n{'='*80}")
        print(f"📋 REFINEMENT SUMMARY")
        print(f"{'='*80}")
        print(f"Total queries tested: {len(self.validations)}")
        print(f"Queries with refinement tracking: {len(refinement_items)}")
        print(f"\nHuman review required to identify specific issues.")
        print(f"Open the HTML report to provide detailed feedback.")
        print(f"{'='*80}\n")
        
        summary = {
            'total_queries': len(self.validations),
            'refinement_tracking_queries': len(refinement_items),
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def _render_mode_comparison_item(self, item):
        """Render mode comparison item as HTML with side-by-side layout"""
        mode_results = item['mode_results']
        
        # Build side-by-side columns for each mode
        modes_html = ""
        for mode_name in ['basic', 'assistant', 'deep', 'both']:
            if mode_name not in mode_results:
                continue
                
            result = mode_results[mode_name]
            mode_config = result['mode_config']
            
            # Determine mode color
            mode_colors = {
                'basic': '#6B7280',  # Gray
                'assistant': '#3B82F6',  # Blue
                'deep': '#8B5CF6',  # Purple
                'both': '#10B981'  # Green
            }
            mode_color = mode_colors.get(mode_name, '#6B7280')
            
            # Build feature badges
            features = []
            if result.get('clarification'):
                features.append('<span class="badge badge-info">🔍 Clarification</span>')
            if result.get('validation'):
                features.append('<span class="badge badge-success">✓ Validation</span>')
            if result.get('metadata', {}).get('features_active', {}).get('disambiguation'):
                features.append('<span class="badge badge-warning">💡 Disambiguation</span>')
            if result.get('hallucination_check', {}).get('checked'):
                is_halluc = result['hallucination_check'].get('is_hallucination', False)
                if is_halluc:
                    features.append('<span class="badge badge-danger">⚠️ Hallucination Detected</span>')
                else:
                    features.append('<span class="badge badge-safe">✅ No Hallucination</span>')
            
            features_html = ' '.join(features) if features else '<span class="badge">No special features</span>'
            
            # Confidence display
            confidence = result['confidence']
            conf_score = confidence.get('score', 0)
            conf_verdict = confidence.get('verdict', 'unknown')
            conf_class = 'high' if conf_score >= 0.7 else 'medium' if conf_score >= 0.5 else 'low'
            
            modes_html += f"""
            <div class="mode-column" style="border-left: 4px solid {mode_color};">
                <div class="mode-header" style="background: {mode_color}20;">
                    <h3 style="color: {mode_color};">{mode_config.name}</h3>
                    <div class="mode-stats">
                        <span class="stat">⏱️ {result['response_time_ms']}ms</span>
                        <span class="stat confidence {conf_class}">🎯 {conf_score:.2f} ({conf_verdict})</span>
                        <span class="stat">📄 {result['sources']} sources</span>
                    </div>
                </div>
                
                <div class="mode-features">
                    {features_html}
                </div>
                
                <div class="mode-answer">
                    <strong>Answer:</strong>
                    <div class="answer-text">{result['answer']}</div>
                </div>
                
                <div class="rating-section">
                    <label>Rate this answer (1-5 ⭐):</label>
                    <div class="star-rating">
                        {''.join(f'<input type="radio" name="rating_{item["id"]}_{mode_name}" value="{i}" id="star_{item["id"]}_{mode_name}_{i}"><label for="star_{item["id"]}_{mode_name}_{i}">⭐</label>' for i in range(1, 6))}
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <div class="validation-item mode-comparison" data-item-id="{item['id']}" data-item-type="mode_comparison">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Mode Comparison - {item['query_type']}</span>
            </div>
            
            <div class="query-info">
                <div class="question">❓ {item['query']}</div>
                <div class="expected">✅ Expected: {item['expected_answer']}</div>
            </div>
            
            <div class="modes-container">
                {modes_html}
            </div>
            
            <div class="validation-form">
                <h4>Overall Assessment:</h4>
                <textarea name="notes_{item['id']}" placeholder="Compare the modes:&#10;&#10;Examples:&#10;- Basic mode was fast but low confidence&#10;- Assistant mode caught the ambiguity and asked for clarification&#10;- Deep Search provided the most thorough validation&#10;- Both mode combined the best features"></textarea>
                
                <div class="best-mode-select">
                    <label><strong>Which mode gave the best answer?</strong></label>
                    <select name="best_mode_{item['id']}">
                        <option value="">Select...</option>
                        <option value="basic">Basic</option>
                        <option value="assistant">Assistant</option>
                        <option value="deep">Deep Search</option>
                        <option value="both">Both</option>
                    </select>
                </div>
            </div>
        </div>
        
        <style>
        .mode-comparison .modes-container {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        
        .mode-column {{
            background: #1e293b;
            border-radius: 8px;
            padding: 15px;
            min-height: 300px;
        }}
        
        .mode-header {{
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        
        .mode-header h3 {{
            margin: 0 0 8px 0;
            font-size: 18px;
        }}
        
        .mode-stats {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            font-size: 13px;
            padding: 4px 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
        }}
        
        .stat.confidence.high {{ background: #10b98180; }}
        .stat.confidence.medium {{ background: #f59e0b80; }}
        .stat.confidence.low {{ background: #ef444480; }}
        
        .mode-features {{
            margin-bottom: 15px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        
        .badge-info {{ background: #3b82f680; }}
        .badge-success {{ background: #10b98180; }}
        .badge-warning {{ background: #f59e0b80; }}
        .badge-danger {{ background: #ef444480; }}
        .badge-safe {{ background: #10b98180; }}
        
        .mode-answer {{
            margin-bottom: 15px;
        }}
        
        .answer-text {{
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 4px;
            margin-top: 8px;
            max-height: 150px;
            overflow-y: auto;
            line-height: 1.5;
        }}
        
        .rating-section {{
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 15px;
        }}
        
        .star-rating {{
            display: flex;
            gap: 5px;
            margin-top: 8px;
            flex-direction: row-reverse;
            justify-content: flex-end;
        }}
        
        .star-rating input[type="radio"] {{
            display: none;
        }}
        
        .star-rating label {{
            font-size: 24px;
            cursor: pointer;
            opacity: 0.3;
            transition: opacity 0.2s;
        }}
        
        .star-rating input[type="radio"]:checked ~ label,
        .star-rating label:hover,
        .star-rating label:hover ~ label {{
            opacity: 1;
        }}
        
        .query-info {{
            background: #1e293b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .query-info .question {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .query-info .expected {{
            font-size: 14px;
            color: #10b981;
        }}
        
        .best-mode-select {{
            margin-top: 15px;
        }}
        
        .best-mode-select select {{
            width: 100%;
            padding: 10px;
            font-size: 14px;
            background: #1e293b;
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 4px;
            margin-top: 8px;
        }}
        </style>
        """
    
    def _render_rag_refinement_item(self, item):
        """Render RAG answer with refinement tracking"""
        contexts_html = ''.join(
            f'<div class="context"><strong>Context {i+1}:</strong> {ctx}</div>' 
            for i, ctx in enumerate(item['contexts'])
        )
        
        # Expected elements checklist
        expected_html = ""
        if item.get('expected_elements'):
            expected_html = '<div class="expected-elements"><h5>✅ Expected Elements:</h5><ul>'
            for elem in item['expected_elements']:
                expected_html += f'<li>{elem}</li>'
            expected_html += '</ul></div>'
        
        # Potential issues checklist
        issues_html = ""
        if item.get('potential_issues'):
            issues_html = '<div class="potential-issues"><h5>⚠️ Check for These Issues:</h5><ul>'
            for issue in item['potential_issues']:
                issues_html += f'<li><input type="checkbox" name="issue_{item["id"]}_{issue[:20]}" value="{issue}"> <label>{issue}</label></li>'
            issues_html += '</ul></div>'
        
        test_name = item['metadata'].get('test_name', 'unknown')
        complexity = item['metadata'].get('complexity', 'medium')
        
        return f"""
        <div class="validation-item refinement-item" data-item-id="{item['id']}" data-item-type="rag_refinement">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Query with Refinement Tracking</span>
                <span class="badge badge-{complexity}">{complexity.upper()} Complexity</span>
                <span class="badge">{test_name}</span>
            </div>
            
            <div class="question">❓ {item['question']}</div>
            
            <div class="answer">
                <strong>Answer:</strong><br>
                {item['answer']}
            </div>
            
            <div class="contexts">
                <strong>Retrieved Contexts ({len(item['contexts'])}):</strong>
                {contexts_html}
            </div>
            
            {expected_html}
            {issues_html}
            
            <div class="validation-form">
                <h4>Your Validation:</h4>
                <div class="radio-group">
                    <div class="radio-option accurate">
                        <input type="radio" id="item{item['id']}_accurate" name="validation_{item['id']}" value="accurate">
                        <label for="item{item['id']}_accurate">✅ Accurate - No Refinement Needed</label>
                    </div>
                    <div class="radio-option partial">
                        <input type="radio" id="item{item['id']}_partial" name="validation_{item['id']}" value="partial">
                        <label for="item{item['id']}_partial">⚠️ Partially Accurate - Minor Refinement</label>
                    </div>
                    <div class="radio-option inaccurate">
                        <input type="radio" id="item{item['id']}_inaccurate" name="validation_{item['id']}" value="inaccurate">
                        <label for="item{item['id']}_inaccurate">❌ Needs Major Refinement</label>
                    </div>
                </div>
                <textarea name="notes_{item['id']}" placeholder="Detailed feedback for refinement:&#10;&#10;- What needs to be fixed?&#10;- Which expected elements are missing?&#10;- Are any of the flagged issues present?&#10;- Suggested improvements"></textarea>
            </div>
        </div>
        
        <style>
        .refinement-item .expected-elements {{
            background: #10b98120;
            padding: 12px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        
        .refinement-item .potential-issues {{
            background: #f59e0b20;
            padding: 12px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        
        .refinement-item ul {{
            margin: 8px 0 0 20px;
            line-height: 1.8;
        }}
        
        .refinement-item ul li {{
            margin-bottom: 6px;
        }}
        
        .badge-high {{ background: #ef444480; color: white; }}
        .badge-very_high {{ background: #dc262680; color: white; }}
        .badge-medium {{ background: #f59e0b80; color: white; }}
        .badge-low {{ background: #10b98180; color: white; }}
        </style>
        """
    
    def _render_multisource_item(self, item):
        """Render multi-source query validation"""
        contexts_html = ''.join(
            f'<div class="context"><strong>Context {i+1}:</strong> {ctx}</div>' 
            for i, ctx in enumerate(item['contexts'])
        )
        
        source_coverage = item['source_coverage']
        required_sources = item['metadata'].get('required_sources', [])
        uploaded_sources = item['metadata'].get('uploaded_sources', [])
        
        # Source coverage visualization
        coverage_html = f"""
        <div class="source-coverage">
            <h5>📊 Source Coverage Analysis:</h5>
            <div class="coverage-stats">
                <div class="stat">
                    <span class="stat-label">Unique Sources Referenced:</span>
                    <span class="stat-value">{source_coverage['unique_sources']} / {len(uploaded_sources)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Coverage:</span>
                    <span class="stat-value">{source_coverage.get('coverage_pct', 0):.0f}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Contexts:</span>
                    <span class="stat-value">{source_coverage.get('total_contexts', 0)}</span>
                </div>
            </div>
        </div>
        """
        
        # Source breakdown
        breakdown_html = "<div class='source-breakdown'><h5>🔍 Source Breakdown:</h5><ul>"
        for source_type, count in source_coverage.get('source_breakdown', {}).items():
            breakdown_html += f"<li><strong>{source_type.upper()}:</strong> {count} contexts</li>"
        breakdown_html += "</ul></div>"
        
        # Required sources checklist
        required_html = ""
        if required_sources:
            required_html = "<div class='required-sources'><h5>✅ Required Sources:</h5><ul>"
            for req_source in required_sources:
                is_covered = req_source in source_coverage.get('source_breakdown', {})
                status_icon = "✅" if is_covered else "❌"
                required_html += f"<li>{status_icon} {req_source.upper()}</li>"
            required_html += "</ul></div>"
        
        return f"""
        <div class="validation-item multisource-item" data-item-id="{item['id']}" data-item-type="multisource">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Multi-Source Query</span>
            </div>
            
            <div class="question">❓ {item['question']}</div>
            
            {coverage_html}
            {breakdown_html}
            {required_html}
            
            <div class="answer">
                <strong>Answer:</strong><br>
                {item['answer']}
            </div>
            
            <div class="contexts">
                <strong>Retrieved Contexts ({len(item['contexts'])}):</strong>
                {contexts_html}
            </div>
            
            <div class="validation-form">
                <h4>Your Validation:</h4>
                <div class="checkbox-group">
                    <h5>Check all that apply:</h5>
                    <div><input type="checkbox" name="cross_ref_{item['id']}" value="yes"> <label>✅ Answer successfully cross-references multiple sources</label></div>
                    <div><input type="checkbox" name="all_sources_{item['id']}" value="yes"> <label>✅ All required sources were consulted</label></div>
                    <div><input type="checkbox" name="synthesis_{item['id']}" value="yes"> <label>✅ Answer synthesizes information (not just listing facts)</label></div>
                    <div><input type="checkbox" name="citations_{item['id']}" value="yes"> <label>✅ Answer cites which source each fact came from</label></div>
                    <div><input type="checkbox" name="missing_source_{item['id']}" value="yes"> <label>⚠️ Important source was not referenced</label></div>
                    <div><input type="checkbox" name="single_source_{item['id']}" value="yes"> <label>⚠️ Answer relies too heavily on single source</label></div>
                </div>
                
                <div class="radio-group" style="margin-top: 20px;">
                    <h5>Overall Rating:</h5>
                    <div class="radio-option accurate">
                        <input type="radio" id="item{item['id']}_accurate" name="validation_{item['id']}" value="accurate">
                        <label for="item{item['id']}_accurate">✅ Excellent Cross-Document Analysis</label>
                    </div>
                    <div class="radio-option partial">
                        <input type="radio" id="item{item['id']}_partial" name="validation_{item['id']}" value="partial">
                        <label for="item{item['id']}_partial">⚠️ Some Cross-Referencing, Needs Improvement</label>
                    </div>
                    <div class="radio-option inaccurate">
                        <input type="radio" id="item{item['id']}_inaccurate" name="validation_{item['id']}" value="inaccurate">
                        <label for="item{item['id']}_inaccurate">❌ Insufficient Multi-Source Analysis</label>
                    </div>
                </div>
                
                <textarea name="notes_{item['id']}" placeholder="Multi-source analysis feedback:&#10;&#10;- Did the answer effectively combine information from multiple documents?&#10;- Which sources were well-utilized?&#10;- Which sources were missing or underutilized?&#10;- How can cross-document reasoning be improved?"></textarea>
            </div>
        </div>
        
        <style>
        .multisource-item .source-coverage {{
            background: #3b82f620;
            padding: 15px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        
        .coverage-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 10px;
        }}
        
        .coverage-stats .stat {{
            text-align: center;
        }}
        
        .stat-label {{
            display: block;
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            display: block;
            font-size: 20px;
            font-weight: bold;
            color: #3b82f6;
        }}
        
        .source-breakdown, .required-sources {{
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        
        .checkbox-group {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 6px;
        }}
        
        .checkbox-group > div {{
            margin-bottom: 10px;
        }}
        </style>
        """
    
    def _render_export_quality_item(self, item):
        """Render export quality validation"""
        export_info = item['export_info']
        cleanup_result = item['cleanup_result']
        expected_outcomes = item['metadata'].get('expected_outcomes', [])
        issues_to_check = item['metadata'].get('issues_to_check', [])
        
        # Export success status
        success_class = "success" if export_info.get('export_successful') else "danger"
        success_icon = "✅" if export_info.get('export_successful') else "❌"
        success_text = "Export Successful" if export_info.get('export_successful') else "Export Failed"
        
        export_details_html = f"""
        <div class="export-status {success_class}">
            <h4>{success_icon} {success_text}</h4>
        </div>
        """
        
        if export_info.get('file_path'):
            export_details_html += f"""
            <div class="export-details">
                <div class="detail-row">
                    <span class="detail-label">File Path:</span>
                    <span class="detail-value"><code>{export_info['file_path']}</code></span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">File Size:</span>
                    <span class="detail-value">{export_info.get('file_size', 0):,} bytes</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Row Count:</span>
                    <span class="detail-value">{export_info.get('row_count', 'N/A'):,}</span>
                </div>
            </div>
            """
            
            if 'remaining_nulls' in export_info:
                nulls_html = "<div class='remaining-nulls'><h5>Remaining Null Values:</h5><ul>"
                for col, count in export_info['remaining_nulls'].items():
                    nulls_html += f"<li><strong>{col}:</strong> {count}</li>"
                nulls_html += "</ul></div>"
                export_details_html += nulls_html
        
        # Cleanup instructions
        cleanup_html = f"""
        <div class="cleanup-instructions">
            <h5>🧹 Cleanup Instructions:</h5>
            <pre>{item['cleanup_instructions']}</pre>
        </div>
        """
        
        # Expected outcomes checklist
        expected_html = ""
        if expected_outcomes:
            expected_html = "<div class='expected-outcomes'><h5>✅ Expected Outcomes:</h5><ul>"
            for outcome in expected_outcomes:
                expected_html += f"<li><input type='checkbox' name='outcome_{item['id']}_{outcome[:20]}' value='{outcome}'> <label>{outcome}</label></li>"
            expected_html += "</ul></div>"
        
        # Issues checklist
        issues_html = ""
        if issues_to_check:
            issues_html = "<div class='issues-checklist'><h5>⚠️ Check for These Issues:</h5><ul>"
            for issue in issues_to_check:
                issues_html += f"<li><input type='checkbox' name='issue_{item['id']}_{issue[:20]}' value='{issue}'> <label>{issue}</label></li>"
            issues_html += "</ul></div>"
        
        return f"""
        <div class="validation-item export-item" data-item-id="{item['id']}" data-item-type="export_quality">
            <div class="item-header">
                <span class="item-number">Item #{item['id'] + 1}</span>
                <span class="item-type">Export Quality Validation</span>
            </div>
            
            {export_details_html}
            {cleanup_html}
            {expected_html}
            {issues_html}
            
            <div class="validation-form">
                <h4>Manual Verification Required:</h4>
                <div class="checkbox-group">
                    <h5>Please verify the exported file:</h5>
                    <div><input type="checkbox" name="file_opens_{item['id']}" value="yes"> <label>✅ File opens correctly in Excel/appropriate app</label></div>
                    <div><input type="checkbox" name="data_correct_{item['id']}" value="yes"> <label>✅ Data cleanup was applied correctly</label></div>
                    <div><input type="checkbox" name="formatting_{item['id']}" value="yes"> <label>✅ Formatting is preserved</label></div>
                    <div><input type="checkbox" name="all_tabs_{item['id']}" value="yes"> <label>✅ All tabs/sheets are present</label></div>
                    <div><input type="checkbox" name="no_corruption_{item['id']}" value="yes"> <label>✅ No data corruption</label></div>
                    <div><input type="checkbox" name="calculations_{item['id']}" value="yes"> <label>✅ Calculated values are correct</label></div>
                </div>
                
                <div class="radio-group" style="margin-top: 20px;">
                    <h5>Overall Export Quality:</h5>
                    <div class="radio-option accurate">
                        <input type="radio" id="item{item['id']}_accurate" name="validation_{item['id']}" value="accurate">
                        <label for="item{item['id']}_accurate">✅ Excellent - Ready for Production Use</label>
                    </div>
                    <div class="radio-option partial">
                        <input type="radio" id="item{item['id']}_partial" name="validation_{item['id']}" value="partial">
                        <label for="item{item['id']}_partial">⚠️ Good - Minor Issues to Address</label>
                    </div>
                    <div class="radio-option inaccurate">
                        <input type="radio" id="item{item['id']}_inaccurate" name="validation_{item['id']}" value="inaccurate">
                        <label for="item{item['id']}_inaccurate">❌ Needs Significant Improvement</label>
                    </div>
                </div>
                
                <textarea name="notes_{item['id']}" placeholder="Export quality feedback:&#10;&#10;- Did cleanup work as expected?&#10;- Are there formatting or data integrity issues?&#10;- Can this file be used for business purposes?&#10;- What needs to be improved?"></textarea>
            </div>
        </div>
        
        <style>
        .export-item .export-status {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin: 12px 0;
        }}
        
        .export-status.success {{
            background: #10b98120;
            border: 2px solid #10b981;
        }}
        
        .export-status.danger {{
            background: #ef444420;
            border: 2px solid #ef4444;
        }}
        
        .export-details {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        
        .detail-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .detail-row:last-child {{
            border-bottom: none;
        }}
        
        .detail-label {{
            font-weight: bold;
            color: #94a3b8;
        }}
        
        .detail-value {{
            color: #e2e8f0;
        }}
        
        .cleanup-instructions pre {{
            background: #1e293b;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        
        .expected-outcomes, .issues-checklist, .remaining-nulls {{
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 6px;
            margin: 12px 0;
        }}
        </style>
        """

