from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

def generatePdf():
    # Output filename
    pdf_filename = "Talent1_Prompts.pdf"

    # Create PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    # Prompts content
    prompts = [
    ("SkillsAssessmentQuestionsGenerationPrompt", '''Based on the following assessment details, generate 10 questions in JSON format:

Assessment Details:
- Title: Introduction to JavaScript
- Category: Programming
- Description: This assessment evaluates understanding of JavaScript fundamentals, syntax, problem solving, and coding best practices.
- Level: Beginner
- Tags: JavaScript, Functions, Arrays, Variables
- Duration: 30 minutes

For each question, include:
1. question_text: Complete question string
2. type: "multiple_choice (single)", "multiple_choice (multiple)", or "coding_challenge"
3. assesses: Array of skills from:
   - "technical knowledge"
   - "problem solving" 
   - "code quality"
   - "best practices"
4. options: Array for MC questions, empty for coding challenges
5. answer_time_limit: Answer time limit in seconds according to assessment total duration and question complexity.

Question Distribution:
- 7 multiple choice (single)
- 2 multiple choice (multiple)
- 1 coding challenge

Guidelines:
- Beginner: Focus on fundamental concepts
- Intermediate: Include practical applications
- Advanced: Add complex problem-solving
- Coding challenges: Clear requirements and edge cases
- Multiple choice: 4 options, 1 correct (2-3 correct for multiple)
- Ensure questions match tags when provided
- Each question must be self contained in text form.

Output ONLY this JSON array:
[
  {
    "question_text": "Which keyword is used to declare a constant in JavaScript?",
    "type": "multiple_choice (single)",
    "assesses": ["technical knowledge"],
    "options": ["var", "let", "const", "define"],
    "answer_time_limit": 60
  }
  // ...remaining questions
]'''),

      ("LanguageAssessmentQuestionsGenerationPrompt", '''Generate exactly 8 complete CEFR-aligned language questions in JSON format based on:

Assessment Details:
- Title: English Language Proficiency Test
- Category: Language Assessment
- Description: This assessment evaluates learners' English proficiency across multiple CEFR levels (A1 to C2) using grammar, vocabulary, comprehension, fluency, and speaking tasks.

Strict Restrictions on Topics:
- Do NOT create questions about personal life, daily routine, family, hobbies, likes/dislikes, or personal experiences.
- All questions must be neutral, situational, or informational, not personal.
- All grammar and vocabulary must be within ~6th grade grammar while aligned with CEFR standard

CEFR Standards Reference:
{
  "A1": "Basic understanding of familiar everyday expressions",
  "A2": "Ability to understand simple sentences and frequently used expressions",
  "B1": "Can deal with most situations likely to arise while travelling",
  "B2": "Can interact with a degree of fluency and spontaneity with native speakers",
  "C1": "Can express ideas fluently and spontaneously without much obvious searching",
  "C2": "Can understand with ease virtually everything heard or read"
}

CEFR Question Samples:
[
  { "level": "A1", "example": "Read this short text and answer one question." },
  { "level": "B1", "example": "Write a short response explaining a situation." },
  { "level": "C1", "example": "Give your opinion on a complex social issue in a structured response." }
]

For each question include:
1. question_text: Complete self-contained question including:
   - For reading: Full 3-5 sentence text
   - For vocabulary: Complete example sentence
   - For audio response questions: Clear speaking instruction without audio dependency
2. type: "short_answer" or "audio" (audio means spoken response by user)
3. assesses: Array of skills from:
   - "fluency" | "grammar" | "naturalness"
   - "pronunciation" | "vocabulary" | "comprehension"
4. options: Always []
5. answer_time_limit: Answer time limit in seconds according to question complexity.

Question Distribution:
- 3 to 4 audio response questions (user speaks answers)
- 4 to 5 short_answer questions including:
  * 2 reading comprehension with full texts
  * 2 vocabulary/grammar in context
  * 1 writing prompt with clear requirements

Level Requirements:
- Must cover at least 4 different CEFR levels
- Include 2 beginner (A1/A2)
- Include 2 intermediate (B1/B2) 
- Include 2 advanced (C1/C2)
- 2 questions can be at any level

Quality Standards:
1. Completeness:
   - No placeholders - all texts included
   - No references to unavailable materials (audio/video)
   - Reading passages: 3-5 complete sentences
   - Writing prompts: Specify required length/format

2. Authenticity:
   - Match real-world use per level
   - Use neutral and situational topics
   - Ensure cultural neutrality

3. Clarity:
   - Unambiguous instructions
   - Appropriate difficulty for each level
   - Directly test target skills

Audio Response Guidelines:
- Must not require listening to any audio

Example Output:
[
  {
    "question_text": "What is one rule people should follow when visiting a library?",
    "type": "audio",
    "assesses": ["fluency"],
    "options": [],
    "answer_time_limit": 30
  }
]
Output ONLY the JSON array with 8 complete questions:'''),

      ("LanguageAssessmentEvaluationPrompt", '''You are an expert English language evaluator. Your task is to assess a user's overall CEFR level based on their responses to multiple evaluation questions.

---

**Reference: CEFR Levels**
Use the CEFR standards below as your reference guide:
{
  "A1": "Basic ability to understand and use familiar everyday expressions.",
  "A2": "Can communicate simple tasks requiring direct exchange of information.",
  "B1": "Can understand main points of clear input and produce simple connected text.",
  "B2": "Can interact with fluency and spontaneity with native speakers.",
  "C1": "Can express ideas fluently, flexibly, and effectively for social, academic, and professional purposes.",
  "C2": "Can understand virtually everything heard or read, and express themselves precisely."
}

---

**Input: Evaluation Data**
The following object contains a list of evaluated questions and their answers. Some questions are open-ended (type: "text") and must be analyzed for grammar, fluency, vocabulary, and pronunciation as appropriate:
[
  {
    "question_text": "Read this passage and explain it in your own words.",
    "type": "text",
    "user_answer": "The text says that people should recycle more because it helps the earth.",
    "evaluated": true
  },
  {
    "question_text": "Give a short spoken response: What rules should people follow in a library?",
    "type": "audio",
    "user_answer": "People should be quiet and respect others.",
    "evaluated": true
  },
  {
    "question_text": "Fill in the blank: She ___ to the store yesterday.",
    "type": "text",
    "user_answer": "went",
    "evaluated": true
  }
]

---

**Instructions:**
1. Analyze all available answers (including type: "text") based on their content and the question context.
2. Do not assess answers that are out of question context.
3. Infer the user's cumulative CEFR level (from A1 to C2) based on the quality of their responses.
4. Consider all core components: pronunciation, grammar, fluency, and vocabulary.
5. Be strict but fair. Do not guess a level if the data is insufficient.

IMPORTANT RULES (must be followed exactly):
1) Pre-conditions: If fewer than 3 answered items are present, OR if there are no text answers and no spoken answers, you MUST return the "Not enough information" JSON (see format below). Do not attempt to guess.
2) Evidence: Your decision MUST be based only on the provided inputs. Do not invent user replies, do not assume unseen speaking samples.

---

**Output Format:**
Respond with this exact format:
{
  "level": "B1 - Intermediate",
  "description": "One-sentence summary of overall ability.",
  "feedback": {
    "pronunciation": "Specific, constructive feedback or suggestions.",
    "grammar": "Specific, constructive feedback or suggestions.",
    "fluency": "Specific, constructive feedback or suggestions.",
    "vocabulary": "Specific, constructive feedback or suggestions."
  }
}

If there is not enough data to make a reliable judgment, return:
{
  "level": "Not enough information",
  "description": "",
  "feedback": {
    "pronunciation": "",
    "grammar": "",
    "fluency": "",
    "vocabulary": ""
  }
}

---

**Rules:**
- Do not include any Markdown, formatting, or explanations—only return the JSON object.
- Do not guess or assume anything not supported by the input.
- Be concise and professional in tone.'''),

      ("QuestionsEvaluationPrompt", '''You are an expert in JavaScript. Below is a list of questions and their corresponding answers from a JavaScript assessment. For each question, evaluate the answer and determine if it is correct or incorrect. Return a JSON object with two properties:
1. "evaluations": An object where each key is the question ID, and the value contains the question text, and score (1 for correct, 0 for incorrect).
2. "overallFeedback": A concise feedback summary (max 100 words) highlighting the user's performance, strengths, and areas for improvement, specific to JavaScript concepts.

Ensure the feedback is constructive and encouraging. Do not include any explanations for individual scores unless requested. Return *only* the JSON object, without any Markdown, code fences, or additional text.
Make sure each object is correct and complete.

Assessment Questions:
Question ID: 1
Question: What is the difference between "let" and "var" in JavaScript?
Answer: "let" is block-scoped, while "var" is function-scoped.

Question ID: 2
Question: What will the expression "2" + 2 evaluate to in JavaScript?
Answer: It evaluates to 4.

Question ID: 3
Question: What is a closure in JavaScript?
Answer: A closure is when a function remembers variables from the outer scope even after that scope has finished executing.

Return the response in the following JSON format:
{
  "evaluations": {
    "1": { "questiontext": "What is the difference between 'let' and 'var' in JavaScript?", "score": 1 },
    "2": { "questiontext": "What will the expression '2' + 2 evaluate to in JavaScript?", "score": 0 },
    "3": { "questiontext": "What is a closure in JavaScript?", "score": 1 }
  },
  "overallFeedback": "The user shows strong understanding of JavaScript concepts like scope and closures. However, they need to review type coercion and operator behavior in JavaScript to avoid common pitfalls."
}'''),

      ("ProfessionSummaryGenerationPrompt", '''Based on the following resume raw text, generate a concise and professional summary (2 sentences) that strictly follows the formatting style and tone of the provided examples. The summary must follow this exact structure:

Sentence 1: Begin with a strong action verb (e.g., spearheaded, scaled, launched, oversaw, developed), clearly stating key achievements with quantifiable impact, relevant metrics, or measurable results; include education background (degree + university) or equivalent credential where applicable; optionally include industry or domain context.

Sentence 2: Short profile validation in this format — "Experienced [role/specialization] from [caliber of companies] with [key skills/strengths]" — optionally add exclusions such as "excludes founder roles."

Rules:
1. Must be exactly 2 sentences.
2. First sentence highlights measurable achievements, tools/technologies, or strategic initiatives.
3. Second sentence validates role, company caliber, and strengths, consistent with provided examples.
4. Follow these example styles exactly:

Examples:
- Spearheaded market research and AI tool development at Larsen & Toubro, enhancing contract analysis for offshore projects; IIT Kanpur graduate. Experienced product/data professional from reputable companies with strong analytics.
- Scaled a B2B platform to $2.6B valuation, led 17x user growth at Tridge, Korea University graduate. Experienced product leader from reputable companies with strong strategy and communication.
- Oversaw 1,000+ real estate transactions, founded a property management firm, saved $6 million with strategic initiatives; UCLA MBA. Experienced operator from top companies with BI and leadership; recent founder role.

Resume Raw Text:
"""
Led cross-functional teams to deliver SaaS solutions adopted by 200+ enterprise clients, generating $15M ARR; B.S. in Computer Science, Stanford University. Prior experience at Microsoft and Stripe with expertise in cloud infrastructure, payments, and API design.
"""
Return only the final 2-sentence summary, with no additional text or formatting.`;'''),

      ("ResumeParsingPrompt", '''You are a highly accurate resume parser. Your job is to extract structured JSON data from a raw resume text, without hallucinating or guessing missing information.
      
Use the following **strict JSON schema**:
{
  "name": string | null,
  "phone": string | null,
  "education": Array<{
    "school": string,
    "degree": string | null,
    "field": string | null,
    "startYear": number | null, // 4-digit year
    "endYear": number | null    // 4-digit year
  }>,
  "experience": Array<{
    "company": string,
    "title": string,
    "description": string | null,
    "startDate": string | null, // ISO date (YYYY-MM-DD) or null
    "endDate": string | null,   // ISO date (YYYY-MM-DD) or null
    "current": boolean          // true if currently working there
  }>,
  "certifications": Array<{
    "name": string,
    "issuer": string | null,
    "year": number | null       // 4-digit year
  }>,
  "skills": Array<string>
}
      
**Parsing Rules:**
- Do NOT fabricate data. Only extract what's clearly mentioned.
- Use null for fields if the required information is missing or ambiguous.
- All date and year fields must follow strict formats (YYYY-MM-DD or YYYY). If they can't be extracted reliably, use null.
- If a section (e.g., certifications) is missing, return an empty array — not null or a guessed entry.
- Names and phone numbers must only be parsed if clearly mentioned.
- Experience must only include jobs explicitly described with a company and role.
- Use double quotes for JSON keys and string values.
      
Resume Text:
"""
John Smith  
Phone: (555) 123-4567  

Education  
- B.S. Computer Science, Stanford University (2012–2016)  

Experience  
- Microsoft — Software Engineer (2016-08-01 to 2019-07-31)  
  Worked on Azure cloud infrastructure, improving deployment tools.  
- Stripe — Senior Software Engineer (2019-08-01 to Present)  
  Led API performance optimization and built scalable payment features.  

Certifications  
- AWS Certified Solutions Architect, Amazon, 2020  

Skills  
JavaScript, TypeScript, Node.js, AWS, SQL, Python
"""
      
Return only the valid JSON response. No comments or explanations.'''),

      ("GenerateInterestedRolesBasedOnCandidateProfile", '''Based on the following candidate profile, analyze and recommend the most suitable interested roles. Consider the candidate's skills, experience, education, certifications, and professional summary.

CANDIDATE PROFILE:

Experience:
- Software Engineer at Microsoft (2018-06-01 - 2021-07-31)
- Senior Software Engineer at Stripe (Current)

Education:
- B.S. in Computer Science from Stanford University (2012-2016)

Certifications:
- AWS Certified Solutions Architect from Amazon (2020)

Professional Summary:
Results-driven software engineer with 7+ years of experience building scalable web applications and cloud-based solutions. Skilled in JavaScript, TypeScript, Node.js, AWS, and API design, with a proven track record of leading projects that improve system performance and reliability.

INSTRUCTIONS:
1. Analyze the candidate's profile comprehensively: experience, education, certifications, and summary.
2. Recommend only roles that realistically match the candidate's demonstrated expertise and career trajectory:
  - Prioritize roles that align with work experience, not just keywords.
  - Do not recommend roles in domains (e.g., backend, DevOps, data science) unless the candidate has clear, direct experience or strong education/certifications in those areas.
  - Do not assume mastery of technologies casually listed unless backed by multiple projects, professional use, or certifications.
3. Consider seniority:
  - Limited or no experience → entry-level roles.
  - 1–3 years experience → junior/mid roles.
  - 4+ years or specialized achievements → senior roles.
4. Recommend 3–5 roles in order of best fit.
5. Ensure recommendations are balanced, realistic, and supportive of the candidate's likely career path.
6. Provide reasoning that explains why these roles align with the candidate's background, avoiding exaggeration.

Return your response as a JSON object with the following structure:
{
  "recommendedRoles": ["role1", "role2", "role3"],
  "reasoning": "Detailed explanation of why these roles are suitable for the candidate"
}

replace prompts varaibled with these udpated ones nothing should be skipped from here''')
  ]

    # Add prompts to PDF, each heading on a new page
    first_section = True
    for title, content in prompts:
        if not first_section:
            story.append(PageBreak())
        story.append(Paragraph(f"<b>{title}</b>", styles['Heading2']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(content.replace("\n", "<br/>"), styles['Normal']))
        story.append(Spacer(1, 12))
        first_section = False

    # Build PDF
    doc.build(story)

    print(f"PDF generated successfully: {pdf_filename}")
