{{> components/section-heading name="sec-activity"}}

{{> components/picture name="activity"}}

<details><summary>최근 활동을 글로 보기 ({{ alts.activity_stamp }} 기준)</summary>

{{#each alts.activity_items}}- <a href="{{ this.url }}">{{ this.repo }}</a>: {{ this.msg }} ({{ this.when }})
{{/each}}
</details>

<sub>modootoday 조직 공개 저장소에서 제가 작성한 커밋만 표시하며, 6시간마다 자동으로 갱신됩니다.</sub>
