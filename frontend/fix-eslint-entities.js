const fs = require('fs');
const path = require('path');

// Files to fix based on ESLint output
const filesToFix = [
  'src/app/auth/success/page.tsx',
  'src/app/dashboard/page.tsx',
  'src/app/integrations/page.tsx',
  'src/app/methodology/page.tsx',
  'src/components/integrations/github-integration-card.tsx',
  'src/components/integrations/slack-integration-card.tsx',
  'src/components/landing-page.tsx',
  'src/components/onboarding-page.tsx',
  'src/components/platform-selection-page.tsx'
];

function escapeQuotesAndApostrophes(content) {
  // Replace quotes and apostrophes in JSX text content
  // This regex matches JSX text content between > and <
  return content.replace(/>([^<]*)</g, (match, text) => {
    const escaped = text
      .replace(/'/g, '&apos;')
      .replace(/"/g, '&quot;');
    return `>${escaped}<`;
  });
}

filesToFix.forEach(filePath => {
  const fullPath = path.join(__dirname, filePath);
  
  try {
    let content = fs.readFileSync(fullPath, 'utf8');
    const originalContent = content;
    
    // More sophisticated replacement that handles JSX text nodes
    content = content.replace(/(['"])([^'"]*['"]+[^'"]*)\1/g, (match, quote, innerText) => {
      // Skip if it's actually a prop value or import
      if (match.includes('=') || match.includes('from') || match.includes('import')) {
        return match;
      }
      
      // Check if this is inside JSX by looking for surrounding > and <
      const startIndex = content.lastIndexOf('>', content.indexOf(match));
      const endIndex = content.indexOf('<', content.indexOf(match));
      
      if (startIndex !== -1 && endIndex !== -1 && startIndex < content.indexOf(match) && endIndex > content.indexOf(match)) {
        // This is JSX text content
        const escaped = innerText
          .replace(/'/g, '&apos;')
          .replace(/"/g, '&quot;');
        return quote + escaped + quote;
      }
      
      return match;
    });
    
    // Additional pass for standalone quotes and apostrophes in JSX text
    content = content.replace(/>([^<]+)</g, (match, text) => {
      // Skip if already escaped
      if (text.includes('&apos;') || text.includes('&quot;')) {
        return match;
      }
      
      const escaped = text
        .replace(/'/g, '&apos;')
        .replace(/"/g, '&quot;');
      return `>${escaped}<`;
    });
    
    if (content !== originalContent) {
      fs.writeFileSync(fullPath, content, 'utf8');
      console.log(`✅ Fixed ${filePath}`);
    } else {
      console.log(`ℹ️  No changes needed for ${filePath}`);
    }
  } catch (error) {
    console.error(`❌ Error processing ${filePath}:`, error.message);
  }
});

console.log('\nDone! Run "npm run lint" to verify all issues are fixed.');