{{> components/section-heading name="sec-services"}}

서비스별 자세한 소개와 저장소는 <a href="https://github.com/modootoday" title="모두의오늘 GitHub 조직 프로필">modootoday 조직 프로필</a>에 있습니다.

<table width="100%">
<thead><tr><th scope="col" width="28%" align="left">서비스</th><th scope="col" width="20%" align="left">대상</th><th scope="col" width="52%" align="left">한 줄 소개</th></tr></thead>
<tbody>
{{#each services}}<tr><td width="28%"><a href="{{ this.url }}" title="{{ this.name }} 웹사이트"><b>{{ this.name }}</b></a><br><sub>{{ this.label }}</sub></td><td width="20%">{{ this.audience }}</td><td width="52%">{{ this.one_line }}</td></tr>
{{/each}}</tbody>
</table>
