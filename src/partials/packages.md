<p align="center">
{{#each packages}}{{> components/card-link href=this.href name=this.svg width="32%"}}
{{/each}}</p>

패키지 {{#each packages}}{{#if @index}} · {{/if}}{{ this.label }} <a href="{{ this.href }}">{{ this.text }}</a>{{/each}}
