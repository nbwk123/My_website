<style>
  .md-nav__item--active > .md-nav__link,
  .md-nav__link--active {
      color: rgb(255, 204, 0) !important;
      font-weight: bold;
  }
</style>

<div class="blogs-page" markdown="1">

<section class="page-hero page-hero--plain course-hero" markdown="1">

<div class="section-heading-line">

<h1>个人分享</h1>

<span style="color:rgba(255,227,113,0.48)!important;">
BLOG
</span>

</div>

记录并分享个人学术经历、生活体验等。

</section>

<!-- 主布局 -->
<div class="side-layout" markdown="1">

<!-- 左侧文章区域 -->
<div class="side-main" markdown="1">

<div class="blog__posts">

<!-- 第一篇文章 -->
<article class="post">

<div class="post__media">

<img class="post__img" src="../assets/2024D20.jpeg" alt="20240627-28-D20大会">

<div class="post-tags">
<span class="post-tag">个人</span>
<span class="post-tag" style="background:rgba(179, 238, 136, 0.46); color: rgb(44, 115, 11);">高校</span>
</div>

</div>

<div class="post__content">

<p class="post__meta">2024-06-27～28 · 会议展会</p>
<h2 class="post__title">2024年D20大会</h2>
<p class="post__excerpt">参加阿里巴巴设计委员会组织的D20大会</p>
<a href="../blogs/2024D20" class="post__link">阅读更多 →</a>

</div>

</article>

<!-- 第二篇文章 -->
<article class="post">

<div class="post__media">

<img class="post__img" src="../assets/Japan_Osaka_Kyoto.jpeg" alt="Example post">

<div class="post-tags">
<span class="post-tag">个人</span>
<span class="post-tag" style="background:rgba(179, 238, 136, 0.46); color: rgb(44, 115, 11);">高校</span>
</div>

</div>

<div class="post__content">

<p class="post__meta">2025-06-30～07-04 · 旅行</p>
<h2 class="post__title">日本·大阪·京都</h2>
<p class="post__excerpt">参加阿里巴巴设计委员会组织的D20大会</p>
<a href="../blogs/2025D20" class="post__link">阅读更多 →</a>

</div>

</article>

<!-- 第三篇文章 -->
<article class="post">

<div class="post__media">

<img class="post__img" src="../assets/2025D20.jpeg" alt="Example post">

<div class="post-tags">
<span class="post-tag">个人</span>
<span class="post-tag" style="background:rgba(179, 238, 136, 0.46); color: rgb(44, 115, 11);">高校</span>
</div>

</div>

<div class="post__content">

<p class="post__meta">2025-07-11 · 会议展会</p>
<h2 class="post__title">2025年D20大会</h2>
<p class="post__excerpt">参加阿里巴巴设计委员会组织的D20大会</p>
<a href="../blogs/2025D20" class="post__link">阅读更多 →</a>

</div>

</article>


<!-- 地球模块的容器 -->
<div style="
  background:#ffffff; 
  border:1px solid #e5e7eb; 
  border-radius:16px; 
  padding:24px; 
  margin-top:40px; 
  width:100%; 
  box-sizing: border-box; 
  box-shadow:0 1px 3px rgba(0,0,0,0.05);
  display: flex; 
  justify-content: center; 
  align-items: center; 
  overflow: hidden;
">
  <div id="globeViz" style="display: flex; justify-content: center; align-items: center; width:100%; height:350px;"></div>
</div>

</div>

<script src="//unpkg.com/globe.gl"></script>
<script>
const container = document.getElementById('globeViz');
if(container){
const myGlobe = Globe()(container)
.globeImageUrl('//unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
.bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
.width(container.clientWidth || 550)
.height(350)
.backgroundColor('rgba(0,0,0,0)');
myGlobe.pointOfView({ altitude:3.5 });
}
</script>

</div>

<!-- 右侧类型栏 -->
<aside class="sidebar">

<div class="side-card">

<p class="side-h">类型</p>

<div class="cat-list">

<a href="#" class="cat cat--active">
<span>所有</span>
<span class="cat__count">31</span>
</a>

<a href="#" class="cat">
<span>旅行记录</span>
<span class="cat__count"></span>
</a>

<a href="#" class="cat">
<span>科研学术</span>
<span class="cat__count">3</span>
</a>

<a href="#" class="cat">
<span>会议展会</span>
<span class="cat__count"></span>
</a>

<a href="#" class="cat">
<span>日常生活</span>
<span class="cat__count">3</span>
</a>

</div>

</div>

</aside>

</div>
<!-- side-layout结束 -->

</div>