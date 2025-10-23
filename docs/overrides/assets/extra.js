// 自定义JavaScript功能

document$.subscribe(function() {
  // 页面加载完成后执行的功能

  // 1. 添加代码块语言标识
  var codeBlocks = document.querySelectorAll('pre code');
  codeBlocks.forEach(function(block) {
    var language = block.className.replace('language-', '');
    if (language && !block.querySelector('.code-language')) {
      var label = document.createElement('div');
      label.className = 'code-language';
      label.textContent = language.toUpperCase();
      label.style.cssText = `
        position: absolute;
        top: 0;
        right: 0;
        padding: 0.2rem 0.5rem;
        background-color: var(--md-default-fg-color--lightest);
        color: var(--md-default-fg-color--light);
        font-size: 0.7rem;
        font-weight: 600;
        border-radius: 0 0.25rem 0 0.25rem;
        z-index: 1;
      `;
      block.style.position = 'relative';
      block.parentElement.style.position = 'relative';
      block.parentElement.appendChild(label);
    }
  });

  // 2. 改进表格响应式处理
  var tables = document.querySelectorAll('.md-typeset table');
  tables.forEach(function(table) {
    if (!table.parentElement.classList.contains('table-wrapper')) {
      var wrapper = document.createElement('div');
      wrapper.className = 'table-wrapper';
      wrapper.style.cssText = `
        overflow-x: auto;
        margin: 1rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      `;
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
  });

  // 3. 添加返回顶部按钮
  var backToTop = document.createElement('button');
  backToTop.innerHTML = '↑';
  backToTop.title = '返回顶部';
  backToTop.style.cssText = `
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    width: 3rem;
    height: 3rem;
    border-radius: 50%;
    background-color: var(--md-accent-fg-color);
    color: white;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  `;

  document.body.appendChild(backToTop);

  // 监听滚动事件
  window.addEventListener('scroll', function() {
    if (window.pageYOffset > 300) {
      backToTop.style.opacity = '1';
      backToTop.style.visibility = 'visible';
    } else {
      backToTop.style.opacity = '0';
      backToTop.style.visibility = 'hidden';
    }
  });

  // 点击返回顶部
  backToTop.addEventListener('click', function() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });

  // 4. 增强搜索功能中文支持
  var searchInput = document.querySelector('.md-search__input');
  if (searchInput) {
    searchInput.setAttribute('placeholder', '搜索文档...');
  }

  // 5. 添加键盘快捷键
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K 打开搜索
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      var searchToggle = document.querySelector('.md-search__form');
      if (searchToggle) {
        searchToggle.querySelector('input').focus();
      }
    }

    // ESC 关闭搜索
    if (e.key === 'Escape') {
      var searchInput = document.querySelector('.md-search__input');
      if (document.activeElement === searchInput) {
        searchInput.blur();
      }
    }
  });

  // 6. 添加页面进度指示器
  var progressBar = document.createElement('div');
  progressBar.className = 'reading-progress';
  progressBar.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    height: 3px;
    background-color: var(--md-accent-fg-color);
    width: 0%;
    transition: width 0.1s ease;
    z-index: 1001;
  `;
  document.body.appendChild(progressBar);

  window.addEventListener('scroll', function() {
    var winScroll = document.body.scrollTop || document.documentElement.scrollTop;
    var height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    var scrolled = (winScroll / height) * 100;
    progressBar.style.width = scrolled + '%';
  });

  // 7. 增强代码块复制功能
  var copyButtons = document.querySelectorAll('.md-clipboard');
  copyButtons.forEach(function(button) {
    button.addEventListener('click', function() {
      var originalTitle = button.getAttribute('title');
      button.setAttribute('title', '已复制!');
      setTimeout(function() {
        button.setAttribute('title', originalTitle);
      }, 2000);
    });
  });

  // 8. 添加外部链接标识
  var externalLinks = document.querySelectorAll('a[href^="http"]:not(.md-social__link)');
  externalLinks.forEach(function(link) {
    if (!link.querySelector('.external-link-icon')) {
      var icon = document.createElement('span');
      icon.innerHTML = ' ↗';
      icon.className = 'external-link-icon';
      icon.style.cssText = `
        font-size: 0.8em;
        opacity: 0.7;
        margin-left: 0.2em;
      `;
      link.appendChild(icon);
    }
  });

  // 9. 增强图片查看功能
  var images = document.querySelectorAll('.md-typeset img');
  images.forEach(function(img) {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', function() {
      // 使用内置的glightbox功能
      if (window.lightbox) {
        lightbox.reload();
      }
    });
  });

  // 10. 添加文档版本信息显示
  var versionInfo = document.createElement('div');
  versionInfo.className = 'docs-version-info';
  versionInfo.style.cssText = `
    position: fixed;
    bottom: 0.5rem;
    left: 0.5rem;
    font-size: 0.7rem;
    color: var(--md-default-fg-color--light);
    opacity: 0.7;
    z-index: 10;
  `;
  versionInfo.textContent = 'v1.0.0 | 最后更新: ' + new Date().toLocaleDateString('zh-CN');
  document.body.appendChild(versionInfo);
});

// 添加自定义CSS到页面
var customCSS = document.createElement('style');
customCSS.textContent = `
  /* 滚动条样式 */
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    background: var(--md-default-bg-color);
  }

  ::-webkit-scrollbar-thumb {
    background: var(--md-default-fg-color--light);
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: var(--md-default-fg-color--lighter);
  }

  /* 搜索建议优化 */
  .md-search-result__item {
    border-bottom: 1px solid var(--md-default-fg-color--lightest);
  }

  .md-search-result__title {
    font-weight: 600;
    color: var(--md-accent-fg-color);
  }

  .md-search-result__teaser {
    line-height: 1.5;
  }

  /* 目录优化 */
  .md-nav--secondary .md-nav__link:hover {
    color: var(--md-accent-fg-color);
  }

  /* 标签页内容优化 */
  .md-typeset .tabbed-content {
    border: 1px solid var(--md-default-fg-color--lightest);
    border-radius: 0 0 6px 6px;
    padding: 1rem;
  }
`;
document.head.appendChild(customCSS);