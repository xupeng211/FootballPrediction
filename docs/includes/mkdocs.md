<!-- MkDocs特定的包含文件 -->

<!-- 添加页面导航快捷键提示 -->
<div class="mkdocs-hint" markdown="1">
**快捷键**:
- `Ctrl/Cmd + K`: 打开搜索
- `ESC`: 关闭搜索
- `↑`: 返回顶部
</div>

<!-- 添加编辑链接提示 -->
{% if page.edit_url %}
<div class="edit-hint" markdown="1">
**发现错误？** [在此页面编辑]({{ page.edit_url }}) 帮助我们改进文档。
</div>
{% endif %}

<!-- 添加反馈链接 -->
<div class="feedback-hint" markdown="1">
**文档反馈**: 如果您有建议或问题，请在 [GitHub]({{ config.repo_url }}/issues) 上提交issue。
</div>