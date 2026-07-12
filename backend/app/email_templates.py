"""
Email templates for OMNI-RANK automated campaigns.
"""

def research_report_email(month_year: str, report_data: dict, subscriber_email: str, unsubscribe_link: str) -> tuple[str, str]:
    """Generate research report email subject and HTML body."""
    subject = f"January 2026 AI Search Report: How AI is Reshaping Search - OMNI-RANK"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #1f2937; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; padding: 40px 20px; text-align: center; }}
            .content {{ padding: 40px 20px; background: white; }}
            .metric {{ background: #f3f4f6; padding: 20px; margin: 15px 0; border-radius: 8px; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #4f46e5; }}
            .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; margin-top: 5px; }}
            .insight {{ border-left: 4px solid #4f46e5; padding: 15px; margin: 15px 0; background: #eef2ff; }}
            .cta {{ text-align: center; margin: 30px 0; }}
            .button {{ background: #4f46e5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">Your January AI Search Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">How AI is reshaping search. Industry by industry.</p>
            </div>

            <div class="content">
                <p>Hi {subscriber_email.split('@')[0].capitalize()},</p>

                <p>Your monthly AI search report is ready. We analyzed 10M+ AI search queries across ChatGPT, Perplexity, Gemini, and Google AI Overviews to show you what's happening in your industry.</p>

                <h2 style="margin-top: 30px; margin-bottom: 20px;">January 2026 Highlights</h2>

                <div class="insight">
                    <strong>SaaS AI Citation Surge</strong><br/>
                    SaaS brands got cited 34% more often in ChatGPT responses this month vs. last month.
                </div>

                <div class="insight">
                    <strong>Comparison Pages Win</strong><br/>
                    68% of AI citations came from comparison pages (vs. product pages at 18%). Your "vs." content matters.
                </div>

                <div class="insight">
                    <strong>E-E-A-T Still Critical</strong><br/>
                    89% of non-cited domains were missing author credentials in their schema. Fix this first.
                </div>

                <div class="insight">
                    <strong>Perplexity Dominance</strong><br/>
                    Perplexity now accounts for 44% of all AI search citations (vs. ChatGPT at 31%). Don't ignore this engine.
                </div>

                <h2 style="margin-top: 30px; margin-bottom: 20px;">Report Includes</h2>
                <ul>
                    <li>Full PDF report (30+ pages) with all data and analysis</li>
                    <li>Monthly metrics spreadsheet for tracking trends</li>
                    <li>Per-industry competitive rankings</li>
                    <li>Next month's predictions from our AI analysts</li>
                    <li>Actionable recommendations for your industry</li>
                </ul>

                <div class="cta">
                    <a href="https://omni-rank.com/research/download?email={subscriber_email}" class="button">Download Full Report</a>
                </div>

                <h2 style="margin-top: 30px; margin-bottom: 20px;">Get Daily Tracking</h2>
                <p>This report shows monthly trends. For real-time AI visibility tracking of YOUR brand, try the OMNI-RANK platform.</p>

                <div class="cta">
                    <a href="https://omni-rank.com/auth/signup" class="button">Try Platform Free</a>
                </div>

                <p style="margin-top: 30px; color: #9ca3af; font-size: 14px;">
                    Next month's report arrives {month_year}. Don't want these emails?<br/>
                    <a href="{unsubscribe_link}" style="color: #4f46e5;">Unsubscribe instantly</a>
                </p>
            </div>

            <div class="footer">
                <p>© 2026 OMNI-RANK. Monthly AI search research report.</p>
                <p>San Francisco, CA | <a href="https://omni-rank.com" style="color: #4f46e5;">omni-rank.com</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html


def nurture_email_1(subscriber_email: str, unsubscribe_link: str) -> tuple[str, str]:
    """Email 1 in nurture sequence: Platform value prop."""
    subject = "Most SaaS companies track the wrong keywords"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ background: #4f46e5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Most SaaS companies track the wrong keywords</h2>
            <p>They focus on volume. Winners focus on conversion.</p>

            <p>Your competitors are ranking for "CRM software" (2.1M searches, 2% convert).</p>
            <p>The winners own "lightweight CRM for startups" (18K searches, 34% convert).</p>

            <p>That's the difference between growth and stagnation.</p>

            <p>OMNI-RANK shows you which keywords actually convert for your vertical. Try it free:</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://omni-rank.com/auth/signup" class="button">See Your Keyword Gaps</a>
            </div>

            <p style="margin-top: 30px; font-size: 12px;">
                <a href="{unsubscribe_link}">Unsubscribe</a>
            </p>
        </div>
    </body>
    </html>
    """

    return subject, html


def nurture_email_2(subscriber_email: str, vertical: str, unsubscribe_link: str) -> tuple[str, str]:
    """Email 2 in nurture sequence: Vertical-specific playbook."""
    subject = f"{vertical.title()} SEO Playbook: What Actually Works"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ background: #4f46e5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>{vertical.title()} SEO Playbook: What Actually Works</h2>
            <p>We analyzed 100+ successful {vertical} companies and found the 3 tactics that drive 80% of their organic growth.</p>

            <p>Download our free playbook to see:</p>
            <ul>
                <li>The keyword clusters winners own</li>
                <li>Content strategies that rank fast</li>
                <li>Competitive gaps you can exploit</li>
            </ul>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://omni-rank.com/blog/{vertical}" class="button">Read the Playbook</a>
            </div>

            <p style="margin-top: 30px; font-size: 12px;">
                <a href="{unsubscribe_link}">Unsubscribe</a>
            </p>
        </div>
    </body>
    </html>
    """

    return subject, html


def nurture_email_3(subscriber_email: str, unsubscribe_link: str) -> tuple[str, str]:
    """Email 3 in nurture sequence: Case study social proof."""
    subject = "How [Company] increased organic revenue by 186%"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ background: #4f46e5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; }}
            .stat {{ background: #f3f4f6; padding: 15px; margin: 15px 0; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>How Acme CRM increased organic revenue by 186%</h2>

            <div class="stat">
                <strong>47 → 207 keywords ranking</strong><br/>
                In just 6 months
            </div>

            <div class="stat">
                <strong>$1.2M → $3.3M ARR from organic</strong><br/>
                Real numbers from a real SaaS company
            </div>

            <p>They used one simple framework: keyword clustering by buyer persona instead of features.</p>

            <p>Read the full case study to see exactly what they did (and how you can repeat it):</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://omni-rank.com/case-studies" class="button">See All Case Studies</a>
            </div>

            <p style="margin-top: 30px; font-size: 12px;">
                <a href="{unsubscribe_link}">Unsubscribe</a>
            </p>
        </div>
    </body>
    </html>
    """

    return subject, html
