#!groovy
timestamps {
    node {
        try {
            checkout scm
            // Checkout submodules
			sh 'git rev-parse HEAD > commit'
			def gitRevision = readFile('commit').trim()
			echo "Revision: ${gitRevision}" 
            sh './project-setup.sh'
            docker.withRegistry('https://5gex.tmit.bme.hu') {
                def image = docker.build("escape:2.0.0.${env.BUILD_NUMBER}", '--build-arg GIT_REVISION=${gitRevision} .')
                image.push('unstable')
            }
			currentBuild.result = 'SUCCESS'
        } catch (any) {
			currentBuild.result = 'FAILURE'
			throw any
		} finally {
			//step([$class: 'Mailer', recipients: '5gex-devel@tmit.bme.hu'])
		}
    }
}
